"""
Ambiguity Detector for FortiGate PM screenshots.
Identifies multi-purpose, composite, and overlapping widget screenshots
where deterministic confidence alone is insufficient.
"""

import re
from typing import List, Dict, Any
from ...models.screenshot import ScreenshotRecord
from .schemas import AmbiguityCheckResult, TriggerCategory

class AmbiguityDetector:
    """
    Detects semantic and scoring ambiguity in screenshot OCR text and classification candidates.
    Triggers AI verification even if top deterministic confidence is >= 0.95.
    """

    KNOWN_OVERLAPPING_PAIRS = [
        {"firmware_version", "system_uptime"},
        {"gui_access", "cpu_usage"},
        {"gui_access", "memory_usage"},
        {"interface", "routing_table"},
        {"license_info", "signature_version"},
    ]

    def detect(self, screenshot: ScreenshotRecord) -> AmbiguityCheckResult:
        reasons: List[str] = []
        candidate_cats: List[str] = [c.category for c in screenshot.classification_candidates]
        text_lower = screenshot.ocr_text.lower()
        candidates = screenshot.classification_candidates

        # 1. Check for Multiple High-Confidence Candidates
        high_conf_candidates = [c for c in candidates if c.confidence >= 0.85]
        if len(high_conf_candidates) >= 2:
            reasons.append(
                f"Multiple strong candidates detected: {', '.join(f'{c.category} ({c.confidence})' for c in high_conf_candidates)}"
            )

        # 2. Check Candidate Score Margin
        if len(candidates) >= 2:
            top_diff = abs(candidates[0].confidence - candidates[1].confidence)
            if candidates[0].confidence >= 0.75 and candidates[1].confidence >= 0.70 and top_diff <= 0.10:
                reasons.append(
                    f"Close competition between top candidates: {candidates[0].category} ({candidates[0].confidence}) vs {candidates[1].category} ({candidates[1].confidence})"
                )

        # 3. Known Overlapping Pairs
        active_categories = {c.category for c in candidates if c.confidence >= 0.70}
        for pair in self.KNOWN_OVERLAPPING_PAIRS:
            if pair.issubset(active_categories):
                reasons.append(f"Known category ambiguity pair detected: {' + '.join(pair)}")

        # 4. Semantic Multi-Widget Detection: System Information Widget (Firmware + Uptime)
        has_sys_info = ("system information" in text_lower) or ("hostname" in text_lower and "serial number" in text_lower)
        has_firmware_markers = any(t in text_lower for t in ["firmware", "v7.", "v6.", "build", "mature"])
        has_uptime_markers = any(t in text_lower for t in ["uptime", "day(s)", "days", "day", "hour", "min"]) or bool(re.search(r"\d+d\s*\d+h|\d+d", text_lower))

        if has_sys_info and has_firmware_markers and has_uptime_markers:
            reasons.append("System Information widget contains co-located evidence for both Firmware and Uptime")
            if "firmware_version" not in candidate_cats:
                candidate_cats.append("firmware_version")
            if "system_uptime" not in candidate_cats:
                candidate_cats.append("system_uptime")

        # 5. Semantic Multi-Widget Detection: Full Dashboard Overview View
        is_dashboard_view = ("/system/dashboard" in text_lower) or ("+ add widget" in text_lower) or ("dashboard/1" in text_lower)
        has_cpu_marker = ("cpu" in text_lower) and ("current usage" in text_lower or "%" in text_lower)
        has_mem_marker = ("memory" in text_lower) and ("current usage" in text_lower or "%" in text_lower)

        if is_dashboard_view and (has_cpu_marker or has_mem_marker):
            reasons.append("Full dashboard screen contains both GUI navigation layout and embedded resource widgets")
            if "gui_access" not in candidate_cats:
                candidate_cats.append("gui_access")
            if has_cpu_marker and "cpu_usage" not in candidate_cats:
                candidate_cats.append("cpu_usage")
            if has_mem_marker and "memory_usage" not in candidate_cats:
                candidate_cats.append("memory_usage")

        is_ambiguous = len(reasons) > 0
        trigger_cat = self.classify_trigger_category(screenshot)

        return AmbiguityCheckResult(
            ambiguous=is_ambiguous,
            reasons=reasons,
            candidate_categories=list(dict.fromkeys(candidate_cats)),
            trigger_category=trigger_cat,
        )

    def classify_trigger_category(self, screenshot: ScreenshotRecord) -> TriggerCategory:
        """
        Classifies potential AI triggers into the formal 6-state taxonomy:
        A. HIGH_CONFIDENCE_MULTI_CATEGORY: Stage 1 confidently detects 2+ valid categories (No AI)
        B. TRUE_LOW_CONFIDENCE: Top candidate confidence < 0.65 (Qwen useful)
        C. OCR_UNRESOLVED: Degraded OCR tokens/text requiring bounded deterministic retry first
        D. PRIMARY_SELECTION_AMBIGUITY: Close margin (<= 0.05) between competing categories
        E. IDENTITY_CONFLICT: Conflicting vendor signatures or negative anchors on top candidate
        F. CLEAR_DETERMINISTIC: High confidence, healthy margin, unambiguous (No AI)
        """
        candidates = screenshot.classification_candidates or []
        tokens = screenshot.ocr_tokens or []
        text_lower = (screenshot.ocr_text or "").lower()

        # C. OCR_UNRESOLVED
        if (len(tokens) <= 3 and (not candidates or candidates[0].confidence < 0.50)) or ("h igh lity moe" in text_lower):
            return TriggerCategory.OCR_UNRESOLVED

        # B. TRUE_LOW_CONFIDENCE
        if not candidates or candidates[0].confidence < 0.65:
            return TriggerCategory.TRUE_LOW_CONFIDENCE

        # E. IDENTITY_CONFLICT (only if top candidate has negative anchor matches)
        if candidates and candidates[0].negative_anchors_matched:
            return TriggerCategory.IDENTITY_CONFLICT

        # A. HIGH_CONFIDENCE_MULTI_CATEGORY
        high_conf = [c for c in candidates if c.confidence >= 0.85]
        if len(high_conf) >= 2:
            return TriggerCategory.HIGH_CONFIDENCE_MULTI_CATEGORY

        # D. PRIMARY_SELECTION_AMBIGUITY
        if len(candidates) >= 2:
            top_diff = abs(candidates[0].confidence - candidates[1].confidence)
            if candidates[0].confidence >= 0.70 and candidates[1].confidence >= 0.70 and top_diff <= 0.05:
                return TriggerCategory.PRIMARY_SELECTION_AMBIGUITY

        # F. CLEAR_DETERMINISTIC
        return TriggerCategory.CLEAR_DETERMINISTIC

ambiguity_detector = AmbiguityDetector()
