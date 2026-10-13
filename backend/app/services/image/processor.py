from pathlib import Path
from PIL import Image, ImageOps
from typing import Tuple

MAX_WORKING_DIMENSION = 3500

def normalize_image(input_path: Path, output_path: Path) -> Tuple[int, int]:
    """
    Normalizes an image:
    1. Validates format.
    2. Transposes according to EXIF rotation.
    3. Converts to RGB (or RGBA if transparent PNG).
    4. Scales down if longest dimension exceeds MAX_WORKING_DIMENSION.
    5. Saves normalized image to output_path.
    Returns (width, height) of normalized image.
    """
    with Image.open(input_path) as img:
        # Correct orientation based on EXIF tag
        img = ImageOps.exif_transpose(img)
        
        # Ensure RGB mode
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
            
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_WORKING_DIMENSION:
            scale = MAX_WORKING_DIMENSION / float(longest)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = img.size
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Save as PNG
        img.save(output_path, format="PNG")
        return w, h

def enhance_contrast_for_ocr_retry(input_path: Path, output_path: Path, upscale_factor: float = 1.5) -> Path:
    """
    Deterministic image preprocessor for OCR retry on difficult/small identity text (serials, hostnames).
    Upscales slightly and enhances contrast to reduce character confusion (e.g. 0 vs 3, 7 vs 1).
    """
    from PIL import ImageEnhance
    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        # Bounded upscale for low-res text
        new_w = int(w * upscale_factor)
        new_h = int(h * upscale_factor)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Grayscale and autocontrast
        img = img.convert("L")
        img = ImageOps.autocontrast(img, cutoff=2)
        
        # Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.4)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        return output_path

