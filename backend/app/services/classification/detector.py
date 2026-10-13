"""
Stage 1: ContentCategoryDetector
Detects PM content categories present in a screenshot.
Supports multi-label semantic content detection.
Separates visible content, URL path, navigation, and regex evidence.
Calculates calibrated confidence and assigns EvidenceQuality.
"""

from typing import Dict, List, Any, Optional
import re

from ...models.screenshot import ScreenshotRecord, OCRToken
from .evidence import (
    EvidenceQuality,
    DetectedContentCategory,
    contains_anchor,
    match_anchor_groups,
    match_regex_patterns,
    partition_ocr_tokens,
    check_label_value_proximity,
)
from .profiles import CATEGORY_PROFILES

class ContentCategoryDetector:
    """
    Stage 1 Detector:
    Answers: 'What PM content exists in this screenshot?'
    Can detect multiple categories simultaneously.
    """

    def detect_categories(self, screenshot: ScreenshotRecord) -> Dict[str, DetectedContentCategory]:
        tokens = screenshot.ocr_tokens or []
        width = screenshot.width or 0
        height = screenshot.height or 0
        raw_text = screenshot.ocr_text or ""
        full_text_lower = raw_text.lower()

        # 1. Geometry Partitioning
        main_tokens, sidebar_tokens, header_tokens = partition_ocr_tokens(tokens, width, height)
        main_text_lower = " ".join(t.text for t in main_tokens).lower() if main_tokens else full_text_lower
        sidebar_text_lower = " ".join(t.text for t in sidebar_tokens).lower() if sidebar_tokens else ""
        header_text_lower = " ".join(t.text for t in header_tokens).lower() if header_tokens else ""

        detected: Dict[str, DetectedContentCategory] = {}

        for category, profile in CATEGORY_PROFILES.items():
            strong_anchors = profile.get("strong_anchors", [])
            strong_groups = profile.get("strong_groups", [])
            supporting_anchors = profile.get("supporting_anchors", [])
            weak_anchors = profile.get("weak_anchors", [])
            negative_anchors = profile.get("negative_anchors", [])
            url_anchors = profile.get("url_anchors", [])
            regex_patterns = profile.get("regex_patterns", [])
            navigation_terms = profile.get("navigation_terms", [])
            requires_label_val = profile.get("requires_label_value", False)

            # 2. Check Strong Anchors in Main Content
            strong_matched = []
            for sa in strong_anchors:
                if contains_anchor(main_text_lower, sa):
                    strong_matched.append(sa)

            # 3. Check Strong Groups in Main Content
            satisfied_groups = match_anchor_groups(main_text_lower, strong_groups)

            # 4. Check Supporting Anchors in Main Content
            supp_matched = []
            for supp in supporting_anchors:
                if contains_anchor(main_text_lower, supp):
                    supp_matched.append(supp)

            # 5. Check URL Anchors (full text/address bar)
            url_matched = []
            for ua in url_anchors:
                if contains_anchor(full_text_lower, ua):
                    url_matched.append(ua)

            # 6. Check Structural Regex Patterns (main text prioritized, full text fallback)
            regex_matched = match_regex_patterns(main_text_lower, regex_patterns)
            if not regex_matched:
                regex_matched = match_regex_patterns(full_text_lower, regex_patterns)

            # 7. Check Negative Anchors
            neg_matched = []
            for na in negative_anchors:
                if contains_anchor(main_text_lower, na) or (('/' in na or 'http' in na) and contains_anchor(full_text_lower, na)):
                    neg_matched.append(na)

            # 8. Check Navigation Contamination
            nav_matched = []
            for nt in navigation_terms:
                if contains_anchor(sidebar_text_lower, nt) or contains_anchor(header_text_lower, nt):
                    nav_matched.append(nt)

            # 9. Local Label-Value Proximity (CPU / Memory)
            has_label_val = True
            if requires_label_val:
                if category == "cpu_usage":
                    has_label_val = check_label_value_proximity(
                        tokens=main_tokens,
                        label_pattern=r"\bcpu\b|\bprocessor\b",
                        val_pattern=r"%|current\s*usage|currentusage|utilization",
                        width=width,
                        height=height,
                        fallback_text=main_text_lower,
                    ) or any("cpu" in m.lower() for m in regex_matched)
                elif category == "memory_usage":
                    has_label_val = check_label_value_proximity(
                        tokens=main_tokens,
                        label_pattern=r"\bmem(?:ory)?\b|\bram\b",
                        val_pattern=r"%|current\s*usage|currentusage|utilization",
                        width=width,
                        height=height,
                        fallback_text=main_text_lower,
                    ) or any("mem" in m.lower() or "ram" in m.lower() for m in regex_matched)

            # 10. Determine Evidence Quality
            n_strong = len(strong_matched) + len(satisfied_groups)
            n_supp = len(supp_matched)
            n_url = len(url_matched)
            n_regex = len(regex_matched)
            n_neg = len(neg_matched)
            n_nav = len(nav_matched)

            # Calculate Component Scores
            visible_content_score = min(1.0, 0.40 * len(strong_matched) + 0.35 * len(satisfied_groups) + 0.10 * n_supp)
            url_path_score = min(1.0, 0.50 * n_url)
            regex_score = min(1.0, 0.40 * n_regex)
            navigation_score = min(0.20, 0.05 * n_nav)

            # Quality categorization
            if requires_label_val and not has_label_val:
                # Missing required label-value relation
                if n_strong == 0 and n_regex == 0:
                    quality = EvidenceQuality.INSUFFICIENT
                else:
                    quality = EvidenceQuality.WEAK
            elif n_strong >= 2 or (n_strong >= 1 and (n_regex >= 1 or n_supp >= 1)) or (n_url >= 1 and (n_strong >= 1 or n_supp >= 2)):
                quality = EvidenceQuality.VERY_STRONG
            elif n_strong >= 1 or (n_regex >= 1 and n_supp >= 1) or (n_url >= 1 and n_supp >= 1) or (len(satisfied_groups) >= 1) or (n_url >= 1):
                quality = EvidenceQuality.STRONG
            elif (n_strong >= 1) or (n_regex >= 1) or (len(satisfied_groups) >= 1) or (n_supp >= 3):
                quality = EvidenceQuality.MODERATE
            elif n_supp >= 1 or any(contains_anchor(main_text_lower, wa) for wa in weak_anchors) or n_nav > 0:
                quality = EvidenceQuality.WEAK
            else:
                quality = EvidenceQuality.INSUFFICIENT

            # If negative anchor matched and evidence isn't overwhelming, downgrade quality
            if n_neg > 0:
                if quality == EvidenceQuality.VERY_STRONG:
                    quality = EvidenceQuality.STRONG
                elif quality == EvidenceQuality.STRONG:
                    quality = EvidenceQuality.MODERATE
                elif quality == EvidenceQuality.MODERATE:
                    quality = EvidenceQuality.WEAK

            # Derive Calibrated Confidence from Evidence Quality
            if quality == EvidenceQuality.VERY_STRONG:
                base_conf = 0.93 + min(0.05, 0.01 * (n_strong + n_supp + n_regex))
            elif quality == EvidenceQuality.STRONG:
                base_conf = 0.86 + min(0.06, 0.015 * (n_supp + n_regex))
            elif quality == EvidenceQuality.MODERATE:
                base_conf = 0.68 + min(0.12, 0.02 * n_supp)
            elif quality == EvidenceQuality.WEAK:
                base_conf = 0.35 + min(0.15, 0.03 * n_supp)
            else:
                base_conf = 0.0

            # Penalties
            if n_neg > 0:
                base_conf = max(0.0, base_conf - 0.20 * n_neg)

            # Isolated navigation penalty
            if n_strong == 0 and n_regex == 0 and n_url == 0 and n_supp <= 1 and n_nav > 0:
                base_conf = min(0.40, base_conf)
                quality = EvidenceQuality.WEAK

            raw_score = round(visible_content_score + url_path_score + regex_score + navigation_score, 4)
            confidence = round(min(0.99, max(0.0, base_conf)), 4)

            reason_parts = []
            if strong_matched:
                reason_parts.append(f"Strong anchors: {', '.join(strong_matched[:3])}")
            if satisfied_groups:
                reason_parts.append(f"Groups: {['+'.join(g) for g in satisfied_groups[:2]]}")
            if url_matched:
                reason_parts.append(f"URL: {', '.join(url_matched[:2])}")
            if regex_matched:
                reason_parts.append(f"Regex: {len(regex_matched)} match(es)")
            if supp_matched:
                reason_parts.append(f"Supporting: {len(supp_matched)} term(s)")
            if neg_matched:
                reason_parts.append(f"Negative: {', '.join(neg_matched[:2])}")
            if n_nav > 0:
                reason_parts.append(f"Nav: {', '.join(nav_matched[:2])}")

            reason_str = " | ".join(reason_parts) if reason_parts else "No significant evidence"

            if confidence > 0.0 or quality != EvidenceQuality.INSUFFICIENT:
                detected[category] = DetectedContentCategory(
                    category=category,
                    raw_score=raw_score,
                    confidence=confidence,
                    evidence_quality=quality,
                    strong_anchors_matched=strong_matched,
                    supporting_anchors_matched=supp_matched,
                    negative_anchors_matched=neg_matched,
                    regex_matches=regex_matched,
                    url_matches=url_matched,
                    navigation_matches=nav_matched,
                    visible_content_score=round(visible_content_score, 4),
                    url_path_score=round(url_path_score, 4),
                    navigation_score=round(navigation_score, 4),
                    regex_score=round(regex_score, 4),
                    reason=reason_str,
                )

        return detected

detector = ContentCategoryDetector()
