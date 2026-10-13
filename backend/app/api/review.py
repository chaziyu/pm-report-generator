from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List
from pathlib import Path
from ..config import settings
from ..models.session import Session
from ..services.rules.engine import rules_engine
from ..services.validation.validator import consistency_validator
from ..services.image.cropper import crop_image

router = APIRouter()

class FieldUpdateRequest(BaseModel):
    field_path: str  # e.g. "hardware.cpu_usage" or "metadata.customer"
    value: Any

class ScreenshotUpdateRequest(BaseModel):
    assigned_category: str

class AppendixUpdateRequest(BaseModel):
    screenshot_id: Optional[str] = None
    crop_bbox: Optional[List[int]] = None  # [x1, y1, x2, y2]
    status: Optional[str] = None

@router.patch("/{session_id}/fields")
def update_field(session_id: str, req: FieldUpdateRequest):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    # Traverse path (e.g. "hardware.cpu_usage" -> session.pm_data.hardware.cpu_usage)
    parts = req.field_path.split(".")
    obj = session.pm_data
    for p in parts[:-1]:
        obj = getattr(obj, p, None)
        if obj is None:
            raise HTTPException(status_code=400, detail=f"Invalid field path section: {p}")

    target_attr = parts[-1]
    extracted_field = getattr(obj, target_attr, None)
    if extracted_field is not None and hasattr(extracted_field, "value"):
        extracted_field.value = req.value
        extracted_field.manually_edited = True
        extracted_field.manually_confirmed = True
    else:
        setattr(obj, target_attr, req.value)

    # Re-evaluate rules & validation
    rules_engine.evaluate(session.pm_data)
    session.validation = consistency_validator.validate(session)

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return {"status": "updated", "field": req.field_path, "value": req.value}

@router.patch("/{session_id}/screenshots/{screenshot_id}")
def update_screenshot_category(session_id: str, screenshot_id: str, req: ScreenshotUpdateRequest):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    sc = next((s for s in session.screenshots if s.id == screenshot_id), None)
    if not sc:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    sc.assigned_categories = [req.assigned_category]
    sc.review_status = "USER_MODIFIED"

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return {"status": "updated", "screenshot_id": screenshot_id, "category": req.assigned_category}

@router.patch("/{session_id}/appendices/{appendix_num}")
def update_appendix(session_id: str, appendix_num: int, req: AppendixUpdateRequest):
    session_dir = settings.workspace_dir / session_id
    session_file = session_dir / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    app_ev = session.pm_data.appendices.get(appendix_num)
    if not app_ev:
        raise HTTPException(status_code=404, detail=f"Appendix {appendix_num} not found")

    if req.screenshot_id:
        app_ev.screenshot_ids = [req.screenshot_id]
        app_ev.status = "CONFIRMED"

    if req.crop_bbox:
        app_ev.crop_bbox = req.crop_bbox
        # Re-crop image if screenshot exists
        if app_ev.screenshot_ids:
            sc = next((s for s in session.screenshots if s.id == app_ev.screenshot_ids[0]), None)
            if sc:
                src_img = Path(sc.normalized_path) if sc.normalized_path else Path(sc.original_path)
                dst_crop = session_dir / "crops" / f"appendix_{appendix_num}.png"
                crop_image(src_img, dst_crop, req.crop_bbox)
                app_ev.crop_path = str(dst_crop)

    if req.status:
        app_ev.status = req.status

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return {"status": "updated", "appendix_number": appendix_num}
