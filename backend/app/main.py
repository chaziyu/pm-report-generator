from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api import sessions, uploads, analysis, review, reports, ai
from .config import settings
import os

app = FastAPI(title="PM Report Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure workspace directory exists
os.makedirs(settings.workspace_dir, exist_ok=True)
app.mount("/workspace", StaticFiles(directory=str(settings.workspace_dir)), name="workspace")

# Include routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(uploads.router, prefix="/api/sessions", tags=["uploads"])
app.include_router(analysis.router, prefix="/api/sessions", tags=["analysis"])
app.include_router(review.router, prefix="/api/sessions", tags=["review"])
app.include_router(reports.router, prefix="/api/sessions", tags=["reports"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])

@app.on_event("shutdown")
def on_app_shutdown():
    from .services.ai.service import local_ai_service
    local_ai_service.runtime_manager.shutdown()

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
