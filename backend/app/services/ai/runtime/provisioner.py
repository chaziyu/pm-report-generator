"""
Provisioner and Installer for Local AI llama.cpp runtime.
Safely downloads, verifies, extracts, and installs llama.cpp locally into bin/llama/.
"""

import os
import sys
import shutil
import zipfile
import threading
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Callable, List

from .manifest import RuntimeManifest, DEFAULT_RUNTIME_MANIFEST

class LocalAIRuntimeProvisioner:
    def __init__(
        self,
        manifest: Optional[RuntimeManifest] = None,
        custom_target_dir: Optional[Path] = None,
    ):
        self.manifest = manifest or DEFAULT_RUNTIME_MANIFEST
        self.custom_target_dir = custom_target_dir
        self._installing = False
        self._progress = 0.0
        self._status_message = ""
        self._error: Optional[str] = None
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()

    def get_target_dir(self) -> Path:
        """Determines the target installation directory (bin/llama)."""
        if self.custom_target_dir:
            return Path(self.custom_target_dir)

        # In frozen application (packaged mode)
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            return exe_dir / "bin" / "llama"

        # In development mode: <repo_root>/bin/llama
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        repo_root = backend_dir.parent
        return repo_root / "bin" / "llama"

    def get_executable_path(self) -> Optional[Path]:
        """Returns the path to llama-server.exe if installed and valid."""
        target_dir = self.get_target_dir()
        exe = target_dir / self.manifest.executable_name
        if exe.exists() and exe.is_file():
            return exe
        return None

    def verify_installed_executable(self, exe_path: Optional[Path] = None) -> Tuple[bool, str, int]:
        """
        Executes llama-server.exe --version to verify the executable launches
        and all required DLLs are resolvable.
        Returns (success, output_or_error, exit_code).
        """
        target_exe = exe_path or self.get_executable_path()
        if not target_exe or not target_exe.exists():
            return False, "Executable not found", -1

        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.run(
                [str(target_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=creationflags,
                cwd=str(target_exe.parent),
            )
            output = (proc.stdout or proc.stderr or "").strip()
            if proc.returncode == 0 or "version:" in output.lower() or "llama" in output.lower() or "build" in output.lower():
                return True, output or f"llama.cpp {self.manifest.runtime_version}", proc.returncode
            return False, output or f"Process exited with code {proc.returncode}", proc.returncode
        except subprocess.TimeoutExpired:
            return False, "Execution timed out", -1
        except Exception as e:
            return False, str(e), -1

    def is_installed_and_ready(self) -> bool:
        """Checks if all required files are present and the executable passes verification."""
        target_dir = self.get_target_dir()
        if not target_dir.exists():
            return False

        # Check required files
        for req_file in self.manifest.required_files:
            p = target_dir / req_file
            if not p.exists():
                return False

        # Verify executable runs
        exe_path = target_dir / self.manifest.executable_name
        ok, _, _ = self.verify_installed_executable(exe_path)
        return ok

    def get_status(self) -> Dict[str, Any]:
        """Returns current provisioner status."""
        with self._lock:
            if self._installing:
                return {
                    "status": "INSTALLING_RUNTIME",
                    "progress": round(self._progress, 1),
                    "message": self._status_message,
                    "error": self._error,
                    "runtime_id": self.manifest.runtime_id,
                }

        if self.is_installed_and_ready():
            ok, ver, code = self.verify_installed_executable()
            return {
                "status": "READY",
                "runtime_id": self.manifest.runtime_id,
                "version": ver,
                "executable": str(self.get_executable_path()),
                "target_dir": str(self.get_target_dir()),
            }

        return {
            "status": "RUNTIME_MISSING",
            "runtime_id": self.manifest.runtime_id,
            "target_dir": str(self.get_target_dir()),
            "message": "Local AI runtime is not installed",
            "error": self._error,
        }

    def start_install_async(
        self,
        offline_mode: bool = False,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> bool:
        """Starts background runtime download and extraction."""
        with self._lock:
            if self._installing:
                return False
            if offline_mode:
                self._error = "Cannot install runtime in offline mode"
                return False

            self._installing = True
            self._progress = 0.0
            self._status_message = "Starting runtime installation"
            self._error = None
            self._cancel_event.clear()

        thread = threading.Thread(
            target=self._run_install,
            args=(on_progress, on_complete),
            daemon=True,
        )
        thread.start()
        return True

    def cancel_install(self) -> None:
        """Cancels an in-progress runtime installation."""
        self._cancel_event.set()

    def install_sync(self, on_progress: Optional[Callable[[float, str], None]] = None) -> bool:
        """Synchronously installs the runtime. Useful for CLI tools, setup scripts, and tests."""
        with self._lock:
            if self._installing:
                raise RuntimeError("Installation already in progress")
            self._installing = True
            self._progress = 0.0
            self._status_message = "Starting installation"
            self._error = None
            self._cancel_event.clear()

        completed = [False]
        error_msg = [None]

        def _done_cb(success: bool, err: Optional[str]):
            completed[0] = success
            error_msg[0] = err

        self._run_install(on_progress, _done_cb)
        if not completed[0]:
            raise RuntimeError(error_msg[0] or "Runtime installation failed")
        return True

    def _update_progress(self, progress: float, msg: str, cb: Optional[Callable[[float, str], None]]) -> None:
        self._progress = progress
        self._status_message = msg
        if cb:
            cb(progress, msg)

    def _run_install(
        self,
        on_progress: Optional[Callable[[float, str], None]],
        on_complete: Optional[Callable[[bool, Optional[str]], None]],
    ) -> None:
        target_dir = self.get_target_dir()
        staging_dir = target_dir.parent / "llama_staging_tmp"
        part_archive = staging_dir / f"{self.manifest.archive_filename}.part"
        extracted_dir = staging_dir / "extracted"

        try:
            staging_dir.mkdir(parents=True, exist_ok=True)
            if extracted_dir.exists():
                shutil.rmtree(extracted_dir, ignore_errors=True)
            extracted_dir.mkdir(parents=True, exist_ok=True)

            # 1. Download
            self._update_progress(5.0, "Connecting to official llama.cpp release...", on_progress)
            req = urllib.request.Request(
                self.manifest.download_url,
                headers={"User-Agent": "PMReportGenerator/1.0 RuntimeProvisioner"},
            )

            with urllib.request.urlopen(req, timeout=45) as resp, open(part_archive, "wb") as out_f:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 256

                while True:
                    if self._cancel_event.is_set():
                        raise InterruptedError("Installation cancelled by user")
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        dl_pct = min(60.0, 5.0 + (downloaded / total_size) * 55.0)
                        self._update_progress(dl_pct, f"Downloading runtime: {downloaded // 1024} KB / {total_size // 1024} KB", on_progress)

            if self._cancel_event.is_set():
                raise InterruptedError("Installation cancelled by user")

            # 2. Checksum verification if available
            if self.manifest.expected_sha256:
                self._update_progress(62.0, "Verifying checksum...", on_progress)
                import hashlib
                h = hashlib.sha256()
                with open(part_archive, "rb") as f:
                    while c := f.read(1024 * 1024):
                        h.update(c)
                actual_hash = h.hexdigest().lower()
                if actual_hash != self.manifest.expected_sha256.lower():
                    raise ValueError(f"Checksum mismatch: expected {self.manifest.expected_sha256}, got {actual_hash}")

            # 3. Extraction
            self._update_progress(65.0, "Extracting runtime files...", on_progress)
            with zipfile.ZipFile(part_archive, "r") as zf:
                zf.extractall(extracted_dir)

            # Locate root of extracted files (handle case where zip includes root folder or flat files)
            search_roots = [extracted_dir]
            for child in extracted_dir.iterdir():
                if child.is_dir():
                    search_roots.append(child)

            extracted_exe: Optional[Path] = None
            resolved_root: Optional[Path] = None
            for root in search_roots:
                candidate = root / self.manifest.executable_name
                if candidate.exists() and candidate.is_file():
                    extracted_exe = candidate
                    resolved_root = root
                    break

            if not extracted_exe or not resolved_root:
                raise FileNotFoundError(f"Archive missing executable: {self.manifest.executable_name}")

            # 4. Verify required DLLs in extracted root
            self._update_progress(78.0, "Verifying extracted files and DLLs...", on_progress)
            for req in self.manifest.required_files:
                p = resolved_root / req
                if not p.exists():
                    raise FileNotFoundError(f"Archive missing required dependency: {req}")

            # 5. Verify extracted executable launches cleanly
            self._update_progress(82.0, "Verifying executable launch compatibility...", on_progress)
            ok, ver_out, exit_code = self.verify_installed_executable(extracted_exe)
            if not ok:
                raise RuntimeError(f"Executable verification failed (exit code {exit_code}): {ver_out}")

            # 6. Atomic move to target_dir
            self._update_progress(90.0, "Finalizing installation into bin/llama...", on_progress)
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            backup_dir = target_dir.parent / "llama_backup_tmp"

            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

            if target_dir.exists():
                target_dir.rename(backup_dir)

            try:
                # Copy or move resolved_root files into target_dir
                shutil.copytree(resolved_root, target_dir)
                if backup_dir.exists():
                    shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception as move_err:
                if backup_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                    backup_dir.rename(target_dir)
                raise move_err

            # 7. Clean up staging
            self._update_progress(98.0, "Cleaning temporary files...", on_progress)
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

            # Final check
            if not self.is_installed_and_ready():
                raise RuntimeError("Runtime installed but post-install health verification failed")

            self._installing = False
            self._progress = 100.0
            self._status_message = "Runtime installed and verified successfully"
            self._error = None

            if on_complete:
                on_complete(True, None)

        except Exception as e:
            self._installing = False
            self._error = str(e)
            self._status_message = f"Failed: {e}"

            # Clean staging files
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

            if on_complete:
                on_complete(False, str(e))
