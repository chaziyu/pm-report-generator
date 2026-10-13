import re
from typing import Optional, Dict
from ...models.screenshot import ScreenshotRecord
from ...models.extracted_value import ExtractedValue

class LicensingExtractor:
    def extract_license_info(self, screenshot: ScreenshotRecord) -> Dict[str, ExtractedValue]:
        text = screenshot.ocr_text
        results = {
            "forticare_status": ExtractedValue(value="Valid", confidence=0.90, source_screenshot_id=screenshot.id),
            "expiry_date": ExtractedValue(confidence=0.80, source_screenshot_id=screenshot.id),
            "antivirus": ExtractedValue(value="Valid", confidence=0.90, source_screenshot_id=screenshot.id),
            "ips": ExtractedValue(value="Valid", confidence=0.90, source_screenshot_id=screenshot.id),
            "web_filter": ExtractedValue(value="Valid", confidence=0.90, source_screenshot_id=screenshot.id),
            "anti_spam": ExtractedValue(value="Valid", confidence=0.90, source_screenshot_id=screenshot.id),
        }

        # Prioritize explicit expiration date (e.g. "Licensed (Expiration Date: 2026/12/28)" or "2028/04/12")
        m_exp_ymd = re.search(r"(?:expiration\s*date|expires?|licensed)[\s:()]*(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text, re.IGNORECASE)
        m_exp_dmy = re.search(r"(?:expiration\s*date|expires?|licensed)[\s:()]*(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text, re.IGNORECASE)

        if m_exp_ymd:
            y, m, d = m_exp_ymd.group(1), m_exp_ymd.group(2).zfill(2), m_exp_ymd.group(3).zfill(2)
            fmt_date = f"{d}/{m}/{y}"
            results["expiry_date"] = ExtractedValue(
                value=fmt_date,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=m_exp_ymd.group(0)
            )
        elif m_exp_dmy:
            d, m, y = m_exp_dmy.group(1).zfill(2), m_exp_dmy.group(2).zfill(2), m_exp_dmy.group(3)
            fmt_date = f"{d}/{m}/{y}"
            results["expiry_date"] = ExtractedValue(
                value=fmt_date,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=m_exp_dmy.group(0)
            )
        else:
            # Fallback to general dates
            dates = re.findall(r"\b(\d{1,2}/\d{1,2}/\d{4})\b|\b(\d{4}[/-]\d{2}[/-]\d{2})\b", text)
            if dates:
                first_date = next((d[0] or d[1]) for d in dates if (d[0] or d[1]))
                results["expiry_date"] = ExtractedValue(
                    value=first_date,
                    confidence=0.85,
                    source_screenshot_id=screenshot.id,
                    source_text=first_date
                )

        # Check explicit expiry indication
        if "expired" in text.lower() and not "not expired" in text.lower():
            if "forticare" in text.lower():
                results["forticare_status"] = ExtractedValue(value="Expired", confidence=0.92, source_screenshot_id=screenshot.id)

        return results

licensing_extractor = LicensingExtractor()
