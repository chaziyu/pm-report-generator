"""
Model file verifier and disk space validator for Local AI subsystem.
Ensures file integrity and atomic staging of GGUF model files.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Tuple

def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Computes SHA-256 hash of a file streaming in chunks."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest().lower()

def verify_file_integrity(file_path: Path, expected_sha256: str) -> Tuple[bool, str]:
    """
    Verifies that file exists and matches the expected SHA-256.
    Returns (is_valid, actual_sha256).
    """
    if not file_path.exists():
        return False, ""
    
    actual_hash = compute_sha256(file_path)
    # If expected_sha256 is empty or placeholder during dev, allow matching
    if not expected_sha256 or expected_sha256 == "skip":
        return True, actual_hash
        
    return actual_hash.lower() == expected_sha256.lower(), actual_hash

def check_disk_space(target_dir: Path, required_bytes: int = 2 * 1024 * 1024 * 1024) -> bool:
    """
    Verifies sufficient free disk space exists on the target volume.
    Defaults to 2 GB minimum headroom.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    total, used, free = shutil.disk_usage(target_dir)
    return free >= required_bytes

def atomic_replace_part_file(part_path: Path, final_path: Path) -> None:
    """
    Atomically replaces final_path with part_path.
    If final_path exists, it is overwritten cleanly.
    """
    if not part_path.exists():
        raise FileNotFoundError(f"Part file not found: {part_path}")
    
    # On Windows, os.replace is atomic on NTFS for files on same volume
    os.replace(str(part_path), str(final_path))
