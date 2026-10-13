from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime, timezone
from ..models.session import Session
from ..models.appendix import AppendixEvidence
from ..services.report.template_map import APPENDIX_MAP, APPENDIX_LOCATORS
from ..config import settings
import json
import os

router = APIRouter()

@router.post("/", response_model=Session)
def create_session():
    session_id = uuid.uuid4().hex[:8]
    session = Session(
        id=session_id,
        status="CREATED",
        created_at=datetime.now(timezone.utc),
    )
    
    # Initialize all 16 appendices
    for cat, num in APPENDIX_MAP.items():
        loc = APPENDIX_LOCATORS.get(num, {})
        title = loc.get("caption", f"Appendix {num}")
        session.pm_data.appendices[num] = AppendixEvidence(
            appendix_number=num,
            title=title,
            category=cat,
            status="MISSING"
        )

    session_dir = settings.workspace_dir / session_id
    os.makedirs(session_dir / "originals", exist_ok=True)
    os.makedirs(session_dir / "normalized", exist_ok=True)
    os.makedirs(session_dir / "crops", exist_ok=True)
    os.makedirs(session_dir / "reports", exist_ok=True)
    
    with open(session_dir / "session.json", "w") as f:
        f.write(session.json(indent=2))
        
    return session

@router.get("/{session_id}", response_model=Session)
def get_session(session_id: str):
    session_file = settings.workspace_dir / session_id / "session.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")
        
    with open(session_file, "r") as f:
        data = f.read()
        
    return Session.parse_raw(data)

@router.delete("/{session_id}")
def delete_session(session_id: str):
    import shutil
    session_dir = settings.workspace_dir / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    shutil.rmtree(session_dir)
    return {"status": "deleted", "id": session_id}
