import shutil
from pathlib import Path
from docx import Document
from ...models.session import Session
from ...config import settings
from .template_map import APPENDIX_LOCATORS
from .tables import update_cover_textboxes, populate_body_tables
from .images import replace_appendix_image
from ..rules.engine import rules_engine

class ReportGenerator:
    def generate_report(self, session: Session) -> Path:
        """
        Generates a completed PM Word report from the pristine template:
        1. Copies pristine template to workspace/<session_id>/reports/<filename>.docx.
        2. Applies rules engine.
        3. Fills cover textboxes and body tables with reviewed PM data.
        4. Replaces appendix screenshot evidence slots.
        5. Saves final document.
        """
        template_file = settings.templates_dir / "preventive-maintenance.docx"
        if not template_file.exists():
            raise FileNotFoundError(f"Pristine template not found at {template_file}")

        # Compute sanitized report filename
        cust = str(session.pm_data.metadata.customer.value or "PM").replace(" ", "_")
        cust_prefix = "".join(c for c in cust if c.isalnum() or c in ("_", "-"))[:15]
        model = str(session.pm_data.application.model.value or "Firewall").replace(" ", "")
        model_clean = "".join(c for c in model if c.isalnum() or c in ("_", "-"))[:10]
        date_str = str(session.pm_data.metadata.pm_date.value or "2026-09-09").replace("/", "-")
        
        filename = f"{cust_prefix}_{model_clean}_PM_{date_str}.docx"

        reports_dir = settings.workspace_dir / session.id / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        target_path = reports_dir / filename

        # Always work on a fresh copy from pristine template
        shutil.copyfile(template_file, target_path)

        # 2. Evaluate rules
        rules_engine.evaluate(session.pm_data)

        # 3. Load copied document
        doc = Document(target_path)

        # 4. Update cover and body tables
        update_cover_textboxes(doc, session.pm_data)
        populate_body_tables(doc, session.pm_data)

        # 5. Replace appendix images
        for app_num, locator in APPENDIX_LOCATORS.items():
            app_evidence = session.pm_data.appendices.get(app_num)
            if not app_evidence:
                continue

            # Check if crop exists or if we should use original/normalized screenshot
            img_to_use = None
            if app_evidence.crop_path and Path(app_evidence.crop_path).exists():
                img_to_use = Path(app_evidence.crop_path)
            elif app_evidence.screenshot_ids:
                sc_id = app_evidence.screenshot_ids[0]
                sc_rec = next((s for s in session.screenshots if s.id == sc_id), None)
                if sc_rec:
                    if sc_rec.normalized_path and Path(sc_rec.normalized_path).exists():
                        img_to_use = Path(sc_rec.normalized_path)
                    elif Path(sc_rec.original_path).exists():
                        img_to_use = Path(sc_rec.original_path)

            if img_to_use and img_to_use.exists():
                # Replace the primary image for this appendix
                primary_rid = locator["embed_rids"][0]
                replace_appendix_image(doc, primary_rid, img_to_use)

        # Save finalized DOCX
        doc.save(target_path)

        # Update session
        session.report_file = filename
        session.report_path = str(target_path)
        session.status = "GENERATED"

        return target_path

report_generator = ReportGenerator()
