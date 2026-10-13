import hashlib
from pathlib import Path
from PIL import Image
from typing import Optional, Tuple, List
from ...models.screenshot import ScreenshotRecord

def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def calculate_dhash(image_path: Path, hash_size: int = 8) -> str:
    """
    Computes difference hash (dHash) for an image.
    Outputs a (hash_size * hash_size) / 4 hex character string (typically 16 hex chars for 64 bits).
    """
    with Image.open(image_path) as img:
        # Convert to grayscale and resize to (hash_size + 1, hash_size)
        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())
        
        # Compare adjacent pixels in each row
        difference = []
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                pixel_left = pixels[row_start + col]
                pixel_right = pixels[row_start + col + 1]
                difference.append(pixel_left > pixel_right)
                
        # Convert boolean list to integer then hex
        decimal_val = 0
        for bit in difference:
            decimal_val = (decimal_val << 1) | int(bit)
            
        hex_len = (hash_size * hash_size) // 4
        return f"{decimal_val:0{hex_len}x}"

def hamming_distance(hex1: str, hex2: str) -> int:
    """Computes Hamming distance between two hex string hashes."""
    try:
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        xor = val1 ^ val2
        return bin(xor).count("1")
    except Exception:
        return 999

def check_duplicate(
    target_sha256: str,
    target_phash: str,
    existing_records: List[ScreenshotRecord],
    near_threshold: int = 5
) -> Tuple[bool, Optional[str], str]:
    """
    Checks if an image is an exact or near duplicate of any existing record.
    Returns (is_duplicate, duplicate_of_id, duplicate_type: "EXACT" | "NEAR" | "NONE")
    """
    for rec in existing_records:
        if rec.sha256 and rec.sha256 == target_sha256:
            return True, rec.id, "EXACT"
            
    for rec in existing_records:
        if rec.perceptual_hash and target_phash:
            dist = hamming_distance(rec.perceptual_hash, target_phash)
            if dist <= near_threshold:
                return True, rec.id, "NEAR"
                
    return False, None, "NONE"
