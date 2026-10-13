"""
Process Controller and Hardware Profiler for bundled llama-server.
Handles binary discovery, hardware detection (RAM / CPU), and process arguments.
"""

import os
import sys
import ctypes
import socket
from pathlib import Path
from typing import Optional, Dict, Any, List

class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def find_free_port(start_port: int = 8081, max_tries: int = 100) -> int:
    """Finds an unused TCP port bound to 127.0.0.1 using OS ephemeral port allocation."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def detect_hardware_profile() -> Dict[str, Any]:
    """
    Detects system RAM and CPU core count using standard library ctypes and os.
    Selects context size based on memory class (<= 8GB -> 2048, > 8GB -> 4096).
    """
    total_gb = 16.0
    avail_gb = 8.0
    if sys.platform == "win32":
        try:
            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_gb = stat.ullTotalPhys / (1024 ** 3)
                avail_gb = stat.ullAvailPhys / (1024 ** 3)
        except Exception:
            pass

    cpu_count = os.cpu_count() or 4

    # Context tuning for low-end hardware (Section 11)
    if total_gb <= 8.5:
        recommended_context = 2048
        profile_name = "low_end_8gb"
    else:
        recommended_context = 4096
        profile_name = "standard_16gb"

    # CPU threads tuning (leave 1 core free for system / backend)
    threads = max(1, min(8, cpu_count - 1)) if cpu_count > 2 else max(1, cpu_count)

    return {
        "total_ram_gb": round(total_gb, 1),
        "available_ram_gb": round(avail_gb, 1),
        "cpu_cores": cpu_count,
        "threads": threads,
        "recommended_context": recommended_context,
        "profile": profile_name,
    }

def find_llama_server_binary(custom_path: Optional[str] = None) -> Optional[Path]:
    """
    Locates llama-server.exe in predictable order (Section 7):
    1. Configured explicit development/runtime path
    2. Bundled repository development folder: <repo_root>/bin/llama/llama-server.exe
    3. Windows packaged directory (alongside frozen executable / in AppData)
    4. Optional PATH fallback for developers only
    """
    binary_names = ["llama-server.exe", "llama-server"]

    # 1. Configured explicit development/runtime path
    if custom_path:
        p = Path(custom_path)
        if p.exists() and p.is_file():
            return p
        if p.is_dir():
            for name in binary_names:
                t = p / name
                if t.exists() and t.is_file():
                    return t

    # 2. Bundled repository development folder: <repo_root>/bin/llama/
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    repo_root = backend_dir.parent
    candidate_dirs = [
        repo_root / "bin" / "llama",
        repo_root / "bin",
        backend_dir / "bin" / "llama",
        backend_dir / "bin",
    ]

    # 3. Windows packaged directory (e.g. alongside frozen executable or in AppData)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidate_dirs.extend([
            exe_dir / "bin" / "llama",
            exe_dir / "llama",
            exe_dir,
        ])
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate_dirs.append(Path(local_app_data) / "CTC" / "PMReportGenerator" / "bin" / "llama")

    for d in candidate_dirs:
        for name in binary_names:
            target = d / name
            if target.exists() and target.is_file():
                return target

    # 4. Optional PATH fallback for developers only
    for path_dir in os.environ.get("PATH", "").split(os.path.pathsep):
        if not path_dir.strip():
            continue
        for name in binary_names:
            target = Path(path_dir) / name
            if target.exists() and target.is_file():
                return target

    return None

def build_llama_server_cmd(
    binary_path: Path,
    model_path: Path,
    port: int,
    context_size: int,
    threads: int,
) -> List[str]:
    """
    Constructs the command line arguments for starting llama-server.
    Enforces localhost-only binding (127.0.0.1), single parallel slot,
    continuous batching, and reasoning budget suppression for fast structured output.
    """
    cmd = [
        str(binary_path),
        "-m", str(model_path),
        "--host", "127.0.0.1",
        "--port", str(port),
        "-c", str(context_size),
        "-t", str(threads),
        "-np", "1",
        "-cb",
        "--reasoning-budget", "0",
    ]
    return cmd

