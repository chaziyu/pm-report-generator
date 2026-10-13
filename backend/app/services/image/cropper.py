from pathlib import Path
from PIL import Image
from typing import List, Optional, Tuple
from ...models.screenshot import OCRToken, ScreenshotRecord, CropCandidate

def find_tokens_by_terms(tokens: List[OCRToken], terms: List[str]) -> List[OCRToken]:
    """Finds all tokens matching any of the search terms (case-insensitive)."""
    matched = []
    lowered_terms = [t.lower() for t in terms]
    for tok in tokens:
        tok_low = tok.text.lower()
        if any(term in tok_low for term in lowered_terms):
            matched.append(tok)
    return matched

def get_enclosing_bbox(tokens: List[OCRToken]) -> Optional[List[int]]:
    """Calculates [min_x, min_y, max_x, max_y] of a set of tokens."""
    if not tokens:
        return None
    min_x = min(t.bbox[0] for t in tokens)
    min_y = min(t.bbox[1] for t in tokens)
    max_x = max(t.bbox[2] for t in tokens)
    max_y = max(t.bbox[3] for t in tokens)
    return [min_x, min_y, max_x, max_y]

def auto_detect_crop(
    screenshot: ScreenshotRecord,
    category: str,
    img_width: int,
    img_height: int,
    padding: int = 25
) -> Optional[List[int]]:
    """
    Computes an optimal cropping bounding box [x1, y1, x2, y2] based on category and anchor positions.
    """
    tokens = screenshot.ocr_tokens
    if not tokens or img_width <= 0 or img_height <= 0:
        return [0, 0, img_width, img_height]

    # Categories that should preserve full tabular/terminal view
    if category in ("interface", "routing_table", "cli_access", "signature_version", "system_event"):
        return [0, 0, img_width, img_height]

    # Target specific widgets for CPU, Memory, License, Firmware, Uptime
    anchors = []
    if category == "cpu_usage":
        anchors = find_tokens_by_terms(tokens, ["cpu", "current", "usage", "%"])
    elif category == "memory_usage":
        anchors = find_tokens_by_terms(tokens, ["memory", "current", "usage", "%"])
    elif category in ("firmware_version", "system_uptime"):
        anchors = find_tokens_by_terms(tokens, ["system", "information", "firmware", "uptime", "hostname"])
    elif category == "license_info":
        anchors = find_tokens_by_terms(tokens, ["license", "licenses", "forticare", "support", "antivirus"])
    elif category == "backup_configuration":
        anchors = find_tokens_by_terms(tokens, ["backup", "system", "download", ".conf"])

    if not anchors:
        return [0, 0, img_width, img_height]

    bbox = get_enclosing_bbox(anchors)
    if not bbox:
        return [0, 0, img_width, img_height]

    # Expand with padding and clamp to image dimensions
    x1 = max(0, bbox[0] - padding * 2)
    y1 = max(0, bbox[1] - padding * 2)
    x2 = min(img_width, bbox[2] + padding * 2)
    y2 = min(img_height, bbox[3] + padding * 2)

    # Ensure crop has reasonable minimum size (at least 200x100)
    if (x2 - x1) < 200:
        center_x = (x1 + x2) // 2
        x1 = max(0, center_x - 150)
        x2 = min(img_width, center_x + 150)
    if (y2 - y1) < 100:
        center_y = (y1 + y2) // 2
        y1 = max(0, center_y - 75)
        y2 = min(img_height, center_y + 75)

    return [x1, y1, x2, y2]

def crop_image(src_path: Path, dst_path: Path, bbox: List[int]):
    """Crops an image using [x1, y1, x2, y2] and saves to dst_path."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as img:
        cropped = img.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
        cropped.save(dst_path, format="PNG")
