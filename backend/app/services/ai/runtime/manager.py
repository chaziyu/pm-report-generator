"""
Runtime Manager for Local AI (llama-server lifecycle).
Implements lazy loading, idle timeout shutdown, free port allocation,
single-concurrency inference lock, and health monitoring.
"""

import sys
import atexit
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from .process import find_free_port, detect_hardware_profile, find_llama_server_binary, build_llama_server_cmd
from .health import check_server_health, wait_for_server_ready
from .provisioner import LocalAIRuntimeProvisioner
from ..model.manager import LocalAIModelManager

class LocalAIRuntimeManager:
    def __init__(
        self,
        model_manager: Optional[LocalAIModelManager] = None,
        provisioner: Optional[LocalAIRuntimeProvisioner] = None,
        custom_binary_path: Optional[str] = None,
        idle_timeout_seconds: int = 300,
        enabled: bool = True,
    ):
        self.model_manager = model_manager or LocalAIModelManager()
        self.provisioner = provisioner or LocalAIRuntimeProvisioner()
        self.custom_binary_path = custom_binary_path
        self.idle_timeout_seconds = idle_timeout_seconds
        self.enabled = enabled

        self._process: Optional[subprocess.Popen] = None
        self._port: Optional[int] = None
        self._last_activity_time: float = 0.0
        self._lock = threading.RLock()
        self._inference_lock = threading.Lock()  # Concurrency = 1
        self._idle_timer_thread: Optional[threading.Thread] = None
        self._stop_idle_checker = threading.Event()
        self.last_generated_cmd: Optional[List[str]] = None

        # Register cleanup on exit
        atexit.register(self.shutdown)

        # Start background idle monitor
        self._start_idle_monitor()

    @property
    def is_running(self) -> bool:
        with self._lock:
            if self._process is None:
                return False
            poll_result = self._process.poll()
            return poll_result is None

    @property
    def base_url(self) -> Optional[str]:
        with self._lock:
            if self._port and self._process and self._process.poll() is None:
                return f"http://127.0.0.1:{self._port}"
            return None

    def get_status(self) -> Dict[str, Any]:
        """Returns overall runtime and model availability status (Section 30)."""
        if not self.enabled:
            return {"status": "DISABLED", "message": "Local AI is disabled"}

        # Check if runtime is currently installing
        prov_status = self.provisioner.get_status()
        if prov_status.get("status") == "INSTALLING_RUNTIME":
            return prov_status

        binary_path = find_llama_server_binary(self.custom_binary_path)
        if not binary_path:
            return {
                "status": "RUNTIME_MISSING",
                "message": "Local AI runtime (llama-server) is not installed",
                "runtime": "llama.cpp",
            }

        model_status = self.model_manager.get_status()
        if model_status["status"] != "READY":
            return {
                "status": model_status["status"],
                "message": f"Model status: {model_status['status']}",
                "model_details": model_status,
            }

        with self._lock:
            if self._process and self._process.poll() is None:
                idle_sec = max(0, int(time.monotonic() - self._last_activity_time))
                return {
                    "status": "RUNNING",
                    "model_loaded": True,
                    "port": self._port,
                    "base_url": f"http://127.0.0.1:{self._port}",
                    "idle_seconds": idle_sec,
                    "timeout_seconds": self.idle_timeout_seconds,
                    "model": model_status["filename"],
                    "last_cmd": self.last_generated_cmd,
                }

        return {
            "status": "READY",
            "model_loaded": False,
            "message": "AI is ready for lazy activation",
            "model": model_status["filename"],
        }

    def ensure_server_running(self, startup_timeout: float = 45.0) -> str:
        """
        Starts the llama-server process if not already running.
        Returns the localhost base URL (e.g. http://127.0.0.1:8081).
        Thread-safe; prevents duplicate processes.
        """
        if not self.enabled:
            raise RuntimeError("Local AI is disabled")

        with self._lock:
            # Check if existing process is healthy
            if self._process and self._process.poll() is None and self._port:
                self._touch_activity()
                return f"http://127.0.0.1:{self._port}"

            binary = find_llama_server_binary(self.custom_binary_path)
            if not binary:
                raise FileNotFoundError("llama-server binary could not be found")

            model_path = self.model_manager.find_model_path()
            if not model_path:
                raise FileNotFoundError(f"Model {self.model_manager.manifest.filename} not found")

            # Check model integrity
            status = self.model_manager.get_status()
            if status["status"] == "CORRUPT_MODEL":
                raise ValueError("Model SHA-256 integrity check failed")

            # Find free local port
            port = find_free_port()
            hw = detect_hardware_profile()

            cmd = build_llama_server_cmd(
                binary_path=binary,
                model_path=model_path,
                port=port,
                context_size=hw["recommended_context"],
                threads=hw["threads"],
            )
            self.last_generated_cmd = cmd

            # Start child process detached from stdin/stdout to avoid hangs
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            log_dir = Path("workspace/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = open(log_dir / "llama_server.log", "a", encoding="utf-8")

            self._process = subprocess.Popen(
                cmd,
                stdout=self._log_file,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
            self._port = port
            self._touch_activity()

        # Wait for health outside lock
        if not wait_for_server_ready(port, timeout_seconds=startup_timeout):
            self.shutdown()
            raise TimeoutError(f"llama-server failed to report ready on 127.0.0.1:{port} within {startup_timeout}s")

        self._touch_activity()
        return f"http://127.0.0.1:{port}"

    def shutdown(self) -> None:
        """Terminates the running llama-server process cleanly."""
        with self._lock:
            if hasattr(self, "_log_file") and self._log_file:
                try:
                    self._log_file.close()
                except Exception:
                    pass
                self._log_file = None
            if self._process:
                try:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                except OSError:
                    pass
                self._process = None
            self._port = None

    def acquire_inference_lock(self):
        """Returns context manager for the single-concurrency inference lock."""
        self._touch_activity()
        return self._inference_lock

    def _touch_activity(self) -> None:
        self._last_activity_time = time.monotonic()

    def _start_idle_monitor(self) -> None:
        def monitor_loop():
            while not self._stop_idle_checker.is_set():
                time.sleep(1)
                if self.is_running and self.idle_timeout_seconds > 0:
                    if self._inference_lock.locked():
                        self._touch_activity()
                        continue
                    idle_duration = time.monotonic() - self._last_activity_time
                    if idle_duration >= self.idle_timeout_seconds:
                        self.shutdown()

        self._idle_timer_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._idle_timer_thread.start()
