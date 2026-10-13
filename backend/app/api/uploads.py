from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import uuid
from pathlib import Path
from ..config import settings
from ..models.session import Session
from ..models.screenshot import ScreenshotRecord
from ..services.image.processor import normalize_image
from ..services.image.duplicate_detector import calculate_sha256, calculate_dhash, check_duplicate

router = APIRouter()

@router.post("/{session_id}/screenshots")
async def upload_screenshot(session_id: str, file: UploadFile = File(...)):
    session_dir = settings.workspace_dir / session_id
    session_file = session_dir / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    # Save original screenshot
    orig_path = session_dir / "originals" / file.filename
    with open(orig_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Calculate hashes
    sha = calculate_sha256(orig_path)
    phash = calculate_dhash(orig_path)

    # Check duplicates against existing screenshots
    is_dup, dup_of, dup_type = check_duplicate(sha, phash, session.screenshots)

    # Normalize image to RGB and scale if needed
    norm_filename = f"norm_{file.filename}"
    norm_path = session_dir / "normalized" / norm_filename
    w, h = normalize_image(orig_path, norm_path)

    record_id = uuid.uuid4().hex[:8]
    rec = ScreenshotRecord(
        id=record_id,
        filename=file.filename,
        original_path=str(orig_path),
        normalized_path=str(norm_path),
        width=w,
        height=h,
        sha256=sha,
        perceptual_hash=phash,
        is_duplicate=is_dup,
        duplicate_of=dup_of,
        review_status="NEEDS_REVIEW" if is_dup else "NOT_REVIEWED"
    )

    session.screenshots.append(rec)
    session.status = "UPLOADED"

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return {
        "id": record_id,
        "filename": file.filename,
        "is_duplicate": is_dup,
        "duplicate_type": dup_type,
        "duplicate_of": dup_of,
        "width": w,
        "height": h
    }
