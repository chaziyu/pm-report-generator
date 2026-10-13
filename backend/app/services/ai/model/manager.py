"""
Model Manager for Local AI subsystem.
Handles model discovery across development and Windows packaged paths,
integrity verification, and secure HTTPS provisioning for the Light Installer.
"""

import os
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .manifest import ModelManifest, DEFAULT_MODEL_MANIFEST
from .verifier import compute_sha256, verify_file_integrity, check_disk_space, atomic_replace_part_file

class LocalAIModelManager:
    def __init__(self, manifest: Optional[ModelManifest] = None, custom_models_dir: Optional[Path] = None):
        self.manifest = manifest or DEFAULT_MODEL_MANIFEST
        self.custom_models_dir = custom_models_dir
        self._downloading = False
        self._download_progress = 0.0
        self._download_error: Optional[str] = None
        self._cancel_download_event = threading.Event()
        self._integrity_cache: Dict[str, Tuple[float, int, bool, str]] = {}
        self._lock = threading.Lock()

    def get_search_paths(self) -> list[Path]:
        """Returns prioritized list of directories to look for GGUF model files."""
        paths = []
        # 1. Custom configured models dir
        if self.custom_models_dir:
            return [Path(self.custom_models_dir)]

        # 2. Workspace development paths: <repo_root>/models/local-ai/ and <backend>/models/
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        repo_root = backend_dir.parent
        paths.append(repo_root / "models" / "local-ai")
        paths.append(repo_root / "models")
        paths.append(backend_dir / "models" / "local-ai")
        paths.append(backend_dir / "models")

        # 3. Windows user AppData path: %LOCALAPPDATA%\CTC\PMReportGenerator\models\
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            paths.append(Path(local_app_data) / "CTC" / "PMReportGenerator" / "models")
            
        return paths

    def get_primary_storage_dir(self) -> Path:
        """Returns the default directory where new downloads should be saved."""
        if self.custom_models_dir:
            return Path(self.custom_models_dir)
            
        # In packaged Windows app, default to LocalAppData
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data and getattr(sys, "frozen", False):
            return Path(local_app_data) / "CTC" / "PMReportGenerator" / "models"
            
        # In dev mode, default to workspace models/local-ai
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        repo_root = backend_dir.parent
        return repo_root / "models" / "local-ai"

    def find_model_path(self) -> Optional[Path]:
        """Locates the existing GGUF model file if present."""
        for directory in self.get_search_paths():
            candidate = directory / self.manifest.filename
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns detailed status of the model file."""
        if self._downloading:
            return {
                "status": "INSTALLING",
                "progress": round(self._download_progress, 1),
                "error": self._download_error,
                "model_id": self.manifest.model_id,
                "filename": self.manifest.filename,
            }

        model_path = self.find_model_path()
        if not model_path:
            return {
                "status": "MODEL_MISSING",
                "model_id": self.manifest.model_id,
                "filename": self.manifest.filename,
                "searched_paths": [str(p) for p in self.get_search_paths()],
            }

        # Check integrity if model exists (cached by mtime and file size)
        stat = model_path.stat()
        cache_key = str(model_path.resolve())
        cached = self._integrity_cache.get(cache_key)
        if cached and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
            valid, hash_val = cached[2], cached[3]
        else:
            valid, hash_val = verify_file_integrity(model_path, self.manifest.expected_sha256)
            self._integrity_cache[cache_key] = (stat.st_mtime, stat.st_size, valid, hash_val)
        if not valid:
            return {
                "status": "CORRUPT_MODEL",
                "model_id": self.manifest.model_id,
                "filename": self.manifest.filename,
                "path": str(model_path),
                "actual_sha256": hash_val,
                "expected_sha256": self.manifest.expected_sha256,
            }

        return {
            "status": "READY",
            "model_id": self.manifest.model_id,
            "filename": self.manifest.filename,
            "path": str(model_path),
            "size_bytes": model_path.stat().st_size,
            "sha256": hash_val,
        }

    def start_download_async(
        self,
        offline_mode: bool = False,
        on_progress: Optional[Callable[[float], None]] = None,
        on_complete: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> bool:
        """
        Initiates background HTTPS download of the model for the Light Installer mode.
        """
        with self._lock:
            if self._downloading:
                return False
            if offline_mode:
                self._download_error = "Cannot download model in offline mode"
                return False
            if not self.manifest.download_url:
                self._download_error = "No download URL configured for model"
                return False

            self._downloading = True
            self._download_progress = 0.0
            self._download_error = None
            self._cancel_download_event.clear()

        thread = threading.Thread(
            target=self._run_download,
            args=(on_progress, on_complete),
            daemon=True,
        )
        thread.start()
        return True

    def cancel_download(self) -> None:
        """Signals download cancellation."""
        self._cancel_download_event.set()

    def _run_download(
        self,
        on_progress: Optional[Callable[[float], None]],
        on_complete: Optional[Callable[[bool, Optional[str]], None]],
    ) -> None:
        target_dir = self.get_primary_storage_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        final_path = target_dir / self.manifest.filename
        part_path = target_dir / f"{self.manifest.filename}.part"

        try:
            # 1. Disk space check
            required_space = max(self.manifest.expected_size_bytes, 2 * 1024 * 1024 * 1024)
            if not check_disk_space(target_dir, required_space):
                raise IOError(f"Insufficient disk space in {target_dir}. At least 2.5 GB required.")

            # 2. Download loop
            req = urllib.request.Request(
                self.manifest.download_url,
                headers={"User-Agent": "PMReportGenerator/1.0 LocalAIProvisioner"},
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp, open(part_path, "wb") as out_f:
                total_size = int(resp.headers.get("content-length", self.manifest.expected_size_bytes or 1))
                downloaded = 0
                chunk_size = 1024 * 512

                while True:
                    if self._cancel_download_event.is_set():
                        raise InterruptedError("Download cancelled by user.")
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    progress = min(100.0, (downloaded / total_size) * 100.0)
                    self._download_progress = progress
                    if on_progress:
                        on_progress(progress)

            # 3. Verify SHA-256
            valid, hash_val = verify_file_integrity(part_path, self.manifest.expected_sha256)
            if not valid:
                raise ValueError(f"Downloaded model SHA-256 mismatch: got {hash_val}, expected {self.manifest.expected_sha256}")

            # 4. Atomic rename
            atomic_replace_part_file(part_path, final_path)
            self._downloading = False
            self._download_progress = 100.0
            if on_complete:
                on_complete(True, None)

        except Exception as e:
            self._download_error = str(e)
            self._downloading = False
            # Clean up part file on failure
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            if on_complete:
                on_complete(False, str(e))
