import re
from typing import Optional, Dict, Any, Tuple
from ...models.screenshot import ScreenshotRecord
from ...models.extracted_value import ExtractedValue

class SystemInfoExtractor:
    def extract_hostname(self, screenshot: ScreenshotRecord) -> Optional[ExtractedValue]:
        text = screenshot.ocr_text
        patterns = [
            r"Hostname\s*[:\s]+([A-Za-z0-9_.-]+)",
            r"Host Name\s*[:\s]+([A-Za-z0-9_.-]+)",
        ]
        ignored_labels = {"serial", "number", "firmware", "mode", "system", "time", "uptime", "wan", "ip", "status", "operation", "ha", "cluster"}

        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                h = m.group(1).strip()
                if len(h) >= 3 and not h.lower().startswith("fortigate") and h.lower() not in ignored_labels:
                    return ExtractedValue(
                        value=h,
                        confidence=0.96,
                        source_screenshot_id=screenshot.id,
                        source_text=m.group(0)
                    )

        # Fallback: look for prominent hostnames matching standard FortiGate naming convention (e.g. HQ-T2fG200F_Primary, HQ_T1_FG201F_INTERNET_FW01)
        m_hn = re.search(r"\b(HQ[-_][A-Za-z0-9_.-]+(?:FW\d*|Primary|Secondary)?)\b", text, re.IGNORECASE)
        if m_hn:
            h = m_hn.group(1).strip()
            # Normalize minor OCR artifacts in hostname if needed (e.g. HQ-T2fG200F_Primary -> HQ_T2_FG200F_Primary)
            h_norm = h.replace("-", "_").replace("fG", "_FG").replace("__", "_")
            return ExtractedValue(
                value=h_norm,
                confidence=0.92,
                source_screenshot_id=screenshot.id,
                source_text=m_hn.group(0)
            )

        return None

    def extract_serials(self, screenshot: ScreenshotRecord) -> Tuple[Optional[ExtractedValue], Optional[ExtractedValue]]:
        text = screenshot.ocr_text
        # FortiGate serials are FG followed by alphanumeric (e.g. FG200FT921916632, FGT60E..., FG201F...)
        serials = re.findall(r"\b(FG[A-Za-z0-9]{10,16})\b", text)
        primary = None
        secondary = None
        if serials:
            # deduplicate preserving order
            unique_serials = list(dict.fromkeys(serials))
            primary = ExtractedValue(
                value=unique_serials[0],
                confidence=0.97,
                source_screenshot_id=screenshot.id,
                source_text=unique_serials[0]
            )
            if len(unique_serials) > 1:
                secondary = ExtractedValue(
                    value=unique_serials[1],
                    confidence=0.95,
                    source_screenshot_id=screenshot.id,
                    source_text=unique_serials[1]
                )
        return primary, secondary

    def extract_firmware(self, screenshot: ScreenshotRecord) -> Dict[str, Optional[ExtractedValue]]:
        text = screenshot.ocr_text
        results = {"version": None, "build": None, "maturity": None, "full_raw": None}

        # 1. Version: Match [6789][._]\d+[._]\d+ guarding against IP address collisions
        m_ver = re.search(
            r"(?<!\d\.)(?:v|firmware\s*(?:version)?\s*v?)?([6789][._]\d+[._]\d+)(?!\.\d)",
            text,
            re.IGNORECASE
        )
        if m_ver:
            raw_ver = m_ver.group(1).replace("_", ".")
            results["version"] = ExtractedValue(
                value=raw_ver,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=m_ver.group(0)
            )

        # 2. Build: Match buildXXXX
        m_bld = re.search(r"\bbuild(\d+)\b", text, re.IGNORECASE)
        if m_bld:
            results["build"] = ExtractedValue(
                value=m_bld.group(1),
                confidence=0.95,
                source_screenshot_id=screenshot.id,
                source_text=m_bld.group(0)
            )

        # 3. Maturity: Mature or Feature in parentheses e.g. (Mature)
        m_mat = re.search(r"\((Mature|Feature)\)", text, re.IGNORECASE)
        if not m_mat:
            m_mat = re.search(r"\b(Mature)\b", text, re.IGNORECASE)
        if m_mat:
            results["maturity"] = ExtractedValue(
                value=m_mat.group(1).capitalize(),
                confidence=0.95,
                source_screenshot_id=screenshot.id,
                source_text=m_mat.group(0)
            )

        return results

    def extract_uptime(self, screenshot: ScreenshotRecord) -> Optional[ExtractedValue]:
        text = screenshot.ocr_text
        # e.g. "51 day(s) 3 hour(s) 44 min(s)" or "177 days 14 hours 24 minutes" or compact "51d 3h44m" / "177d14h24m"
        # 1. Compact format: 51d 3h44m or 177d14h24m
        m_compact = re.search(r"(\d+)\s*d\s*(\d+)\s*h\s*(\d+)\s*m", text, re.IGNORECASE)
        if m_compact:
            d, h, m = m_compact.group(1), m_compact.group(2), m_compact.group(3)
            val = f"{d} day(s) {h} hour(s) {m} min(s)"
            return ExtractedValue(
                value=val,
                confidence=0.98,
                source_screenshot_id=screenshot.id,
                source_text=m_compact.group(0)
            )

        patterns = [
            r"(\d+\s*day\(s\)\s*\d+\s*hour\(s\)\s*\d+\s*min\(s\))",
            r"(\d+\s*days?\s*\d+\s*hours?\s*\d+\s*minutes?)",
            r"Uptime\s*[:\s]*([^\n,]+(?:day|hour|min)[^\n,]+)",
            r"(\d+\s*days?,\s*\d+\s*hours?,\s*\d+\s*minutes?)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return ExtractedValue(
                    value=m.group(1).strip(),
                    confidence=0.97,
                    source_screenshot_id=screenshot.id,
                    source_text=m.group(0)
                )
        return None

    def extract_timezone(self, screenshot: ScreenshotRecord) -> Optional[ExtractedValue]:
        text = screenshot.ocr_text
        patterns = [
            r"\b(GMT\s*[+-]\s*\d+)\b",
            r"\b(Asia/[A-Za-z_]+)\b",
            r"\b(Kuala\s*Lumpur)\b",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                matched = m.group(0)
                val = "GMT +8" if "8" in matched or "kuala" in matched.lower() else matched
                return ExtractedValue(
                    value=val,
                    confidence=0.95,
                    source_screenshot_id=screenshot.id,
                    source_text=matched
                )
        return None

system_info_extractor = SystemInfoExtractor()
