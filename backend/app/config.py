from pydantic import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    workspace_dir: Path = base_dir / "workspace"
    templates_dir: Path = base_dir / "templates"
    datasets_dir: Path = workspace_dir / "datasets" / "pm_reports"

    class Config:
        env_file = ".env"

settings = Settings()
