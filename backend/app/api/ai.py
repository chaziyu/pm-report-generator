"""
FastAPI router for Local AI status and lifecycle management.
Exposes status, download initiation, and diagnostics without leaking internal ports to normal users.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..services.ai.service import local_ai_service
from ..config import settings

router = APIRouter()

@router.get("/status")
def get_ai_status() -> Dict[str, Any]:
    """Returns local AI availability and runtime state for frontend status indicators."""
    status_info = local_ai_service.get_status()
    # Mask internal port and localhost URLs for security in normal UI payload
    safe_status = {
        "status": status_info.get("status", "DISABLED"),
        "model_id": status_info.get("model", "Qwen3-1.7B-Q4_K_M.gguf"),
        "model_loaded": status_info.get("model_loaded", False),
        "enabled": getattr(settings, "ai_enabled", True),
        "message": status_info.get("message", ""),
    }
    if "progress" in status_info:
        safe_status["progress"] = status_info["progress"]
    if "error" in status_info and status_info["error"]:
        safe_status["error"] = status_info["error"]
    return safe_status

@router.post("/runtime/install")
def trigger_runtime_install() -> Dict[str, Any]:
    """Triggers background installation of the llama.cpp runtime."""
    if not getattr(settings, "ai_enabled", True):
        raise HTTPException(status_code=400, detail="Local AI is disabled")

    offline_mode = getattr(settings, "ai_offline_mode", False)
    started = local_ai_service.runtime_manager.provisioner.start_install_async(offline_mode=offline_mode)
    if not started:
        raise HTTPException(
            status_code=400,
            detail=local_ai_service.runtime_manager.provisioner._error or "Runtime installation already in progress or disallowed"
        )
    return {"message": "Runtime installation started", "status": "INSTALLING_RUNTIME"}

@router.post("/runtime/cancel-install")
def cancel_runtime_install() -> Dict[str, Any]:
    """Cancels ongoing runtime installation."""
    local_ai_service.runtime_manager.provisioner.cancel_install()
    return {"message": "Runtime installation cancellation requested"}

@router.post("/setup")
def trigger_unified_setup() -> Dict[str, Any]:
    """
    Unified 'Set up Local AI' action:
    Automatically installs the runtime if missing, or downloads the model if missing.
    """
    if not getattr(settings, "ai_enabled", True):
        raise HTTPException(status_code=400, detail="Local AI is disabled")

    offline_mode = getattr(settings, "ai_offline_mode", False)
    status_info = local_ai_service.get_status()
    st = status_info.get("status")

    if st == "RUNTIME_MISSING":
        started = local_ai_service.runtime_manager.provisioner.start_install_async(offline_mode=offline_mode)
        if not started:
            raise HTTPException(status_code=400, detail="Runtime installation already in progress")
        return {"action": "runtime_install", "message": "Installing Local AI runtime", "status": "INSTALLING_RUNTIME"}

    if st == "MODEL_MISSING":
        started = local_ai_service.model_manager.start_download_async(offline_mode=offline_mode)
        if not started:
            raise HTTPException(status_code=400, detail="Model download already in progress")
        return {"action": "model_download", "message": "Downloading model", "status": "INSTALLING"}

    return {"action": "none", "message": "Local AI is already prepared", "status": st}

@router.post("/download")
def trigger_model_download() -> Dict[str, Any]:
    """Triggers background download for the Light Installer mode."""
    if not getattr(settings, "ai_enabled", True):
        raise HTTPException(status_code=400, detail="Local AI is disabled")
    
    offline_mode = getattr(settings, "ai_offline_mode", False)
    started = local_ai_service.model_manager.start_download_async(offline_mode=offline_mode)
    if not started:
        raise HTTPException(
            status_code=400,
            detail=local_ai_service.model_manager._download_error or "Download already in progress or disallowed"
        )
    return {"message": "Download started", "status": "INSTALLING"}

@router.post("/cancel-download")
def cancel_model_download() -> Dict[str, Any]:
    """Cancels ongoing model download."""
    local_ai_service.model_manager.cancel_download()
    return {"message": "Download cancellation requested"}

