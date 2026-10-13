"""
Report importer orchestrator for PM Report Dataset Importer.
Coordinates extraction of screenshots, appendix mapping, ground truth expected values,
duplicate detection, and immutability verification.
"""

import datetime
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import docx

from .dataset_manifest import (
    ReportManifest,
    DatasetIndex,
    CaseIndexEntry,
    ImportSummary,
)
from .image_extractor import extract_images_and_appendices
from .expected_value_extractor import extract_expected_values

def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def is_supported_fortigate_pm(doc: docx.Document) -> Tuple[bool, str]:
    """
    Validates whether the DOCX document is a supported FortiGate PM report.
    Returns (is_supported, detected_variant_or_reason).
    """
    # 1. Check Model in table
    model_name = ""
    for t in doc.tables[:5]:
        for r in t.rows:
            if len(r.cells) >= 2 and r.cells[0].text.strip().lower() == "model":
                model_name = r.cells[1].text.strip()
                break
        if model_name:
            break

    if model_name:
        if "checkpoint" in model_name.lower():
            return False, "unsupported_template_variant: Check Point report"
        if "fortianalyzer" in model_name.lower() or "fortimanager" in model_name.lower():
            return False, "unsupported_template_variant: FortiAnalyzer/FortiManager report"
        if "fortigate" in model_name.lower() or "fg-" in model_name.lower() or "fg" in model_name.lower():
            return True, "fortigate_pm_v1"

    # 2. Check for characteristic FortiGate PM tables/captions
    fortigate_pm_terms = ["forticare", "utm bundle", "firewall firmware version", "appendix 1-cpu usage", "appendix 1 – cpu usage"]
    doc_text_sample = ""
    for t in doc.tables[:12]:
        for r in t.rows:
            doc_text_sample += " " + " ".join(c.text.lower() for c in r.cells)
            if len(doc_text_sample) > 5000:
                break

    matched_terms = [t for t in fortigate_pm_terms if t in doc_text_sample]
    if len(matched_terms) >= 2:
        return True, "fortigate_pm_v1"

    return False, "unsupported_template_variant: template structure does not match FortiGate PM specification"

class ReportImporter:
    """
    Main importer service to process completed PM reports into a structured validation dataset.
    """

    def __init__(self, output_dir: Path, overwrite: bool = False, copy_source: bool = False):
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.copy_source = copy_source
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_existing_cases(self) -> Dict[str, Path]:
        """
        Scans output_dir for existing cases.
        Returns a mapping of source_sha256 -> case_dir.
        """
        cases: Dict[str, Path] = {}
        if not self.output_dir.exists():
            return cases

        for child in self.output_dir.iterdir():
            if child.is_dir() and child.name.startswith("case_"):
                manifest_path = child / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sha = data.get("source_sha256")
                            if sha:
                                cases[sha] = child
                    except Exception:
                        pass
        return cases

    def import_single_report(
        self,
        docx_path: Path,
        existing_cases: Optional[Dict[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Imports a single completed PM DOCX report.
        """
        if not docx_path.exists():
            return {
                "status": "failed",
                "error": f"File does not exist: {docx_path}",
                "report": docx_path.name
            }

        # 1. Source Immutability Check: Compute SHA256 before
        sha_before = calculate_sha256(docx_path)

        # 2. Check for duplicate
        if existing_cases is None:
            existing_cases = self.get_existing_cases()

        if sha_before in existing_cases and not self.overwrite:
            existing_case_dir = existing_cases[sha_before]
            return {
                "status": "duplicate",
                "report": docx_path.name,
                "case_id": existing_case_dir.name,
                "message": f"Duplicate report already imported in {existing_case_dir.name}"
            }

        # 3. Read and inspect DOCX without modifying it
        try:
            doc = docx.Document(docx_path)
        except Exception as e:
            return {
                "status": "failed",
                "report": docx_path.name,
                "error": f"Failed to open DOCX: {str(e)}"
            }

        is_supported, variant_info = is_supported_fortigate_pm(doc)
        if not is_supported:
            return {
                "status": "unsupported_template_variant",
                "report": docx_path.name,
                "reason": variant_info
            }

        # 4. Extract expected values first to determine model and FSMS ID for clean naming
        expected_values, val_warnings = extract_expected_values(doc)

        model_str = expected_values.get("application", {}).get("model") or "fortigate"
        model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model_str.lower()).strip("_")
        case_id = f"case_{sha_before[:10]}_{model_slug}"
        case_dir = self.output_dir / case_id

        # Clean or prepare target case directory
        if case_dir.exists() and self.overwrite:
            shutil.rmtree(case_dir)

        images_dir = case_dir / "images"
        appendices_dir = case_dir / "appendices"
        images_dir.mkdir(parents=True, exist_ok=True)
        appendices_dir.mkdir(parents=True, exist_ok=True)

        if self.copy_source:
            source_dir = case_dir / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(docx_path, source_dir / docx_path.name)

        # 5. Extract images and map appendices
        image_entries, appendix_entries, img_warnings = extract_images_and_appendices(
            docx_path=docx_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        all_warnings = val_warnings + img_warnings

        # 6. Verify source immutability
        sha_after = calculate_sha256(docx_path)
        assert sha_before == sha_after, f"CRITICAL: Source report {docx_path} was modified during import!"

        # 7. Write expected.json
        expected_path = case_dir / "expected.json"
        with open(expected_path, "w", encoding="utf-8") as f:
            json.dump(expected_values, f, indent=2)

        # 8. Write manifest.json
        manifest = ReportManifest(
            case_id=case_id,
            source_report=str(docx_path.resolve()),
            source_sha256=sha_before,
            imported_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            template_variant=variant_info,
            images=image_entries,
            appendices=appendix_entries,
            warnings=all_warnings
        )
        manifest_path = case_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.dict(), f, indent=2)

        # Count mapped appendices with >= 1 image
        mapped_appendices_count = sum(1 for a in appendix_entries.values() if len(a.images) > 0)
        extracted_screenshot_count = sum(len(a.images) for a in appendix_entries.values())

        return {
            "status": "imported",
            "case_id": case_id,
            "report": docx_path.name,
            "model": expected_values.get("application", {}).get("model"),
            "hostname": expected_values.get("application", {}).get("hostname"),
            "source_sha256": sha_before,
            "appendices_found": mapped_appendices_count,
            "screenshots_extracted": extracted_screenshot_count,
            "warnings_count": len(all_warnings),
            "warnings": all_warnings
        }

    def import_batch(self, input_path: Path) -> Tuple[ImportSummary, List[Dict[str, Any]]]:
        """
        Imports a batch of DOCX files from a directory or a single file.
        Generates dataset.json and import_summary.json.
        """
        docx_files: List[Path] = []
        if input_path.is_file():
            if input_path.suffix.lower() == ".docx":
                docx_files.append(input_path)
        elif input_path.is_dir():
            docx_files = sorted([
                p for p in input_path.glob("*.docx")
                if not p.name.startswith("~$")  # Exclude MS Word temporary lock files
            ])

        summary = ImportSummary()
        summary.reports_scanned = len(docx_files)
        results: List[Dict[str, Any]] = []

        existing_cases = self.get_existing_cases()

        for idx, doc_path in enumerate(docx_files, 1):
            res = self.import_single_report(doc_path, existing_cases=existing_cases)
            results.append(res)

            status = res.get("status")
            if status == "imported":
                summary.reports_imported += 1
                summary.appendices_found += res.get("appendices_found", 0)
                summary.appendices_missing += (16 - res.get("appendices_found", 0))
                # Count non-null expected values
                expected_json_path = self.output_dir / res["case_id"] / "expected.json"
                if expected_json_path.exists():
                    try:
                        with open(expected_json_path, "r", encoding="utf-8") as f:
                            exp_data = json.load(f)
                            for section_val in exp_data.values():
                                if isinstance(section_val, dict):
                                    for k, v in section_val.items():
                                        if v is not None:
                                            summary.expected_fields_extracted += 1
                                        else:
                                            summary.unresolved_fields += 1
                    except Exception:
                        pass

                # Update existing_cases in memory so later files in the batch detect duplicates
                existing_cases[res["source_sha256"]] = self.output_dir / res["case_id"]

            elif status == "duplicate":
                summary.duplicate_reports += 1
            elif status == "unsupported_template_variant":
                summary.unsupported_template_variants += 1
            elif status == "failed":
                summary.reports_failed += 1

        # Rebuild dataset.json index
        self._rebuild_dataset_index()

        # Write import_summary.json
        summary_path = self.output_dir / "import_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary.dict(), f, indent=2)

        return summary, results

    def _rebuild_dataset_index(self):
        """Rebuilds the top-level dataset.json file."""
        entries: List[CaseIndexEntry] = []
        for child in sorted(self.output_dir.iterdir()):
            if child.is_dir() and child.name.startswith("case_"):
                manifest_path = child / "manifest.json"
                expected_path = child / "expected.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                        model = None
                        hostname = None
                        if expected_path.exists():
                            with open(expected_path, "r", encoding="utf-8") as ef:
                                edata = json.load(ef)
                                model = edata.get("application", {}).get("model")
                                hostname = edata.get("application", {}).get("hostname")

                        app_count = sum(
                            1 for a in mdata.get("appendices", {}).values()
                            if len(a.get("images", [])) > 0
                        )
                        screenshot_count = sum(
                            len(a.get("images", []))
                            for a in mdata.get("appendices", {}).values()
                        )
                        entry = CaseIndexEntry(
                            case_id=mdata.get("case_id", child.name),
                            report=Path(mdata.get("source_report", "")).name,
                            model=model,
                            hostname=hostname,
                            appendix_count=app_count,
                            screenshot_count=screenshot_count,
                            warnings=len(mdata.get("warnings", [])),
                            source_sha256=mdata.get("source_sha256", "")
                        )
                        entries.append(entry)
                    except Exception:
                        pass

        dataset_index = DatasetIndex(cases=entries)
        index_path = self.output_dir / "dataset.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(dataset_index.dict(), f, indent=2)
