from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from ..config import settings
from ..models.session import Session
from ..services.validation.validator import consistency_validator
from ..services.report.generator import report_generator

router = APIRouter()

@router.post("/{session_id}/validate")
def validate_session(session_id: str):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    issues = consistency_validator.validate(session)
    session.validation = issues

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    blocking_errors = [i for i in issues if i.blocking]
    return {
        "is_valid": len(blocking_errors) == 0,
        "total_issues": len(issues),
        "blocking_count": len(blocking_errors),
        "issues": [i.dict() for i in issues]
    }

@router.post("/{session_id}/reports")
def generate_docx_report(session_id: str):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    # Pre-generation validation check
    issues = consistency_validator.validate(session)
    session.validation = issues
    blocking_errors = [i for i in issues if i.blocking]
    if blocking_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Report generation blocked by {len(blocking_errors)} critical consistency error(s)."
        )

    out_path = report_generator.generate_report(session)

    with open(session_file, "w") as f:
        f.write(session.json(indent=2))

    return {
        "status": "generated",
        "filename": session.report_file,
        "download_url": f"/api/sessions/{session_id}/reports/download"
    }

@router.get("/{session_id}/reports/download")
def download_report(session_id: str):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(session_file, "r") as f:
        session = Session.parse_raw(f.read())

    if not session.report_path or not Path(session.report_path).exists():
        raise HTTPException(status_code=404, detail="Report has not been generated yet.")

    return FileResponse(
        path=session.report_path,
        filename=session.report_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
