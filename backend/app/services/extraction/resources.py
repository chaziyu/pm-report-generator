import re
from typing import Optional, Tuple
from ...models.screenshot import ScreenshotRecord
from ...models.extracted_value import ExtractedValue

def extract_percentage(text: str, label: str) -> Optional[Tuple[int, str]]:
    """
    Extracts percentage value associated with label (e.g. CPU or Memory).
    Returns (percentage_int, matched_raw_text) or None.
    """
    other_label = "memory" if label.lower() == "cpu" else "cpu"
    patterns = [
        # Label followed by (current) usage X% without crossing into the other resource label
        rf"{label}(?:(?!{other_label}).)*?(?:current\s*)?usage(?:(?!{other_label}).)*?(\d+)%",
        rf"{label}(?:(?!{other_label}).)*?(\d+)%\s*usage",
        rf"{label}(?:(?!{other_label}).)*?(\d+)%",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val, m.group(0)
    return None

class ResourceExtractor:
    def extract_cpu(self, screenshot: ScreenshotRecord) -> Optional[ExtractedValue]:
        res = extract_percentage(screenshot.ocr_text, "CPU")
        if res:
            val, raw = res
            return ExtractedValue(
                value=val,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=raw,
            )
        return None

    def extract_memory(self, screenshot: ScreenshotRecord) -> Optional[ExtractedValue]:
        res = extract_percentage(screenshot.ocr_text, "Memory")
        if res:
            val, raw = res
            return ExtractedValue(
                value=val,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=raw,
            )
        return None

resource_extractor = ResourceExtractor()
