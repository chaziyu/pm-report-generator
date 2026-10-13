import re
from typing import Optional, Dict
from ...models.screenshot import ScreenshotRecord
from ...models.extracted_value import ExtractedValue

class VpnExtractor:
    def extract_vpn_stats(self, screenshot: ScreenshotRecord) -> Dict[str, ExtractedValue]:
        text = screenshot.ocr_text
        results = {
            "total": ExtractedValue(value=0, confidence=0.85, source_screenshot_id=screenshot.id),
            "active": ExtractedValue(value=0, confidence=0.85, source_screenshot_id=screenshot.id),
            "inactive": ExtractedValue(value=0, confidence=0.85, source_screenshot_id=screenshot.id),
        }

        # Look for "tunnels:? total: (\d+)"
        m_total = re.search(r"tunnels:?\s*total:\s*(\d+)", text, re.IGNORECASE)
        tot = 0
        if m_total:
            tot = int(m_total.group(1))
            results["total"] = ExtractedValue(value=tot, confidence=0.98, source_screenshot_id=screenshot.id, source_text=m_total.group(0))

        # Check for static/ddns active tunnels count (e.g. static/ddns: 74) or selectors up count
        m_static = re.search(r"static/ddns:?\s*(\d+)", text, re.IGNORECASE)
        m_sel = re.search(r"selectors:?.*?total:\s*(\d+).*?up:\s*(\d+)", text, re.IGNORECASE | re.DOTALL)

        if m_static and tot > 0:
            act = int(m_static.group(1))
            results["active"] = ExtractedValue(value=act, confidence=0.96, source_screenshot_id=screenshot.id, source_text=m_static.group(0))
            results["inactive"] = ExtractedValue(value=max(0, tot - act), confidence=0.96, source_screenshot_id=screenshot.id)
        elif m_sel:
            sel_total = int(m_sel.group(1))
            sel_up = int(m_sel.group(2))
            act = min(tot, sel_up) if tot > 0 else sel_up
            results["active"] = ExtractedValue(value=act, confidence=0.96, source_screenshot_id=screenshot.id, source_text=f"up: {sel_up}")
            results["inactive"] = ExtractedValue(value=max(0, tot - act), confidence=0.96, source_screenshot_id=screenshot.id)

        return results

vpn_extractor = VpnExtractor()
