from fastapi import APIRouter, HTTPException
from pathlib import Path
from ..config import settings
from ..models.session import Session
from ..services.ocr.service import ocr_service
from ..services.classification.classifier import classifier
from ..services.image.cropper import auto_detect_crop, crop_image
from ..services.extraction.extractor import master_extractor
from ..services.rules.engine import rules_engine
from ..services.validation.validator import consistency_validator
from ..services.report.template_map import APPENDIX_MAP

router = APIRouter()

@router.post("/{session_id}/analyze", response_model=Session)
def run_analysis(session_id: str):
    session_dir = settings.workspace_dir / session_id
    session_file = session_dir / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    session.status = "PROCESSING"

    # 1. Run OCR and classification for each screenshot
    for sc in session.screenshots:
        img_to_ocr = Path(sc.normalized_path) if sc.normalized_path and Path(sc.normalized_path).exists() else Path(sc.original_path)
        
        # Only run OCR if not already processed
        if not sc.ocr_tokens:
            try:
                tokens, full_text = ocr_service.process_image(img_to_ocr)
                sc.ocr_tokens = tokens
                sc.ocr_text = full_text
            except Exception as e:
                print(f"OCR error on {sc.filename}: {e}")

        # Classify
        classifier.classify(sc)

        # Ambiguity detection & Local AI verification
        from ..services.ai.service import local_ai_service
        ambiguity = local_ai_service.check_ambiguity(sc)
        sc.is_ambiguous = ambiguity.ambiguous
        sc.ambiguity_reasons = ambiguity.reasons

        top_cand = sc.classification_candidates[0] if sc.classification_candidates else None
        top_cat = top_cand.category if top_cand else "unknown"
        top_conf = top_cand.confidence if top_cand else 0.0

        state, final_cats, provenance = local_ai_service.verify_classification(
            screenshot=sc,
            deterministic_category=top_cat,
            deterministic_confidence=top_conf,
        )
        sc.arbitration_state = state.value
        sc.assigned_categories = final_cats
        if provenance:
            sc.ai_provenance = provenance.dict()

    # 2. Select best screenshot for each of the 16 appendices
    for cat_name, app_num in APPENDIX_MAP.items():
        candidates = []
        for sc in session.screenshots:
            if sc.is_duplicate:
                continue
            # Find confidence for this category
            cand = next((c for c in sc.classification_candidates if c.category == cat_name), None)
            if cand:
                candidates.append((sc, cand.confidence))
            elif cat_name in sc.assigned_categories:
                candidates.append((sc, 0.90))

        if candidates:
            # Sort by highest confidence
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_sc, conf = candidates[0]
            
            app_ev = session.pm_data.appendices.get(str(app_num)) or session.pm_data.appendices.get(app_num)
            if app_ev:
                app_ev.screenshot_ids = [best_sc.id]
                app_ev.confidence = conf
                app_ev.status = "DETECTED" if conf >= 0.80 else "REVIEW_REQUIRED"

                # 3. Auto-crop container panel
                norm_img_path = Path(best_sc.normalized_path) if best_sc.normalized_path else Path(best_sc.original_path)
                crop_box = auto_detect_crop(best_sc, cat_name, best_sc.width, best_sc.height)
                if crop_box:
                    crop_dst = session_dir / "crops" / f"appendix_{app_num}.png"
                    crop_image(norm_img_path, crop_dst, crop_box)
                    app_ev.crop_path = str(crop_dst)
                    app_ev.crop_bbox = crop_box

    # 4. Structured extraction
    master_extractor.extract_all(session.screenshots, session.pm_data)

    # 5. PM Rules Engine
    rules_engine.evaluate(session.pm_data)

    # 6. Consistency Validation
    session.validation = consistency_validator.validate(session)

    session.status = "REVIEW_REQUIRED"

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return session

@router.get("/{session_id}/analysis")
def get_analysis_status(session_id: str):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    detected_count = sum(1 for a in session.pm_data.appendices.values() if a.screenshot_ids)
    return {
        "status": session.status,
        "total_screenshots": len(session.screenshots),
        "detected_appendices": detected_count,
        "total_appendices": len(APPENDIX_MAP),
        "validation_issues_count": len(session.validation)
    }
