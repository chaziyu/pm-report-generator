"""
Local In-Memory and Filesystem Cache for Local AI results.
Prevents redundant LLM inferences across duplicate runs and identical OCR payloads.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any

def compute_cache_key(
    screenshot_hash: str,
    ocr_text_hash: str,
    task_type: str,
    model_revision: str,
    prompt_version: str,
) -> str:
    payload = f"{screenshot_hash}:{ocr_text_hash}:{task_type}:{model_revision}:{prompt_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

class LocalAICache:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        # 1. In-memory check
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # 2. Disk check
        if self.cache_dir:
            file_p = self.cache_dir / f"{cache_key}.json"
            if file_p.exists():
                try:
                    with open(file_p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._memory_cache[cache_key] = data
                        return data
                except Exception:
                    pass
        return None

    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        self._memory_cache[cache_key] = data
        if self.cache_dir:
            file_p = self.cache_dir / f"{cache_key}.json"
            try:
                with open(file_p, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception:
                pass

    def clear(self) -> None:
        self._memory_cache.clear()

ai_cache = LocalAICache()
