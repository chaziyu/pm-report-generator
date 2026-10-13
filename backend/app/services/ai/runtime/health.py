"""
Health and readiness checker for local llama-server.
"""

import time
import urllib.request
import urllib.error
import json
from typing import Dict, Any, Tuple

def check_server_health(port: int, timeout_sec: float = 1.0) -> Tuple[bool, str]:
    """
    Polls http://127.0.0.1:{port}/health.
    Returns (is_ready, status_message).
    """
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PMReportGenerator/HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                status = data.get("status", "ok")
                if status == "ok":
                    return True, "READY"
                elif status == "loading model":
                    return False, "LOADING_MODEL"
                return False, status
            return False, f"HTTP_{resp.status}"
    except urllib.error.URLError:
        return False, "UNREACHABLE"
    except Exception as e:
        return False, str(e)

def wait_for_server_ready(port: int, timeout_seconds: float = 45.0, poll_interval: float = 0.5) -> bool:
    """
    Blocks until the server reports status == 'ok' or timeout expires.
    """
    start_time = time.monotonic()
    while (time.monotonic() - start_time) < timeout_seconds:
        ready, msg = check_server_health(port)
        if ready:
            return True
        time.sleep(poll_interval)
    return False
