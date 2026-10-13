"""
Evidence model and geometric/text analysis utilities for Classifier V2.
"""

from enum import Enum
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from ...models.screenshot import OCRToken

class EvidenceQuality(str, Enum):
    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"

class DetectedContentCategory(BaseModel):
    category: str
    raw_score: float
    confidence: float
    evidence_quality: EvidenceQuality
    strong_anchors_matched: List[str] = []
    supporting_anchors_matched: List[str] = []
    negative_anchors_matched: List[str] = []
    regex_matches: List[str] = []
    url_matches: List[str] = []
    navigation_matches: List[str] = []
    visible_content_score: float = 0.0
    url_path_score: float = 0.0
    navigation_score: float = 0.0
    regex_score: float = 0.0
    confidence_margin: float = 0.0
    reason: str = ""

def contains_anchor(text: str, anchor: str) -> bool:
    """Robust anchor matcher handling regex and word boundaries."""
    anchor_clean = anchor.lower().strip()
    if not anchor_clean:
        return False
    # If anchor contains regex metacharacters, search as regex
    if any(ch in anchor_clean for ch in r"\.*+?[](){}|^$"):
        try:
            return bool(re.search(anchor_clean, text, re.IGNORECASE))
        except re.error:
            pass
    # Alphanumeric words need word boundary to avoid substring collisions
    if anchor_clean.isalnum():
        pattern = rf"\b{re.escape(anchor_clean)}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))
    return anchor_clean in text

def match_anchor_groups(text: str, groups: List[List[str]]) -> List[List[str]]:
    """Checks if all items in a group are present in text."""
    satisfied = []
    for grp in groups:
        if all(contains_anchor(text, term) for term in grp):
            satisfied.append(grp)
    return satisfied

def match_regex_patterns(text: str, patterns: List[str]) -> List[str]:
    """Finds all regex matches in text."""
    matched = []
    for pat in patterns:
        try:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                matched.append(m.group(0))
        except re.error:
            continue
    return matched

def partition_ocr_tokens(
    tokens: List[OCRToken],
    width: int,
    height: int,
) -> Tuple[List[OCRToken], List[OCRToken], List[OCRToken]]:
    """
    Partitions OCR tokens into:
    1. main_panel_tokens
    2. sidebar_tokens (left navigation drawer on full-page screenshots)
    3. header_tokens (top bar region on full-page screenshots)
    """
    if width < 800 or height < 500 or not tokens:
        return tokens, [], []

    # Check if this screenshot actually has FortiOS sidebar navigation drawer
    nav_markers = {"dashboard", "network", "system", "security profiles", "vpn", "log & report", "fortiview"}
    left_tokens = [t for t in tokens if t.bbox and len(t.bbox) == 4 and t.bbox[2] <= width * 0.25]
    left_text = " ".join(t.text.lower() for t in left_tokens)
    has_nav_drawer = sum(1 for m in nav_markers if m in left_text) >= 2

    if not has_nav_drawer:
        # Not a full page with navigation drawer; all tokens are main panel
        return tokens, [], []

    main_panel: List[OCRToken] = []
    sidebar: List[OCRToken] = []
    header: List[OCRToken] = []

    for t in tokens:
        if not t.bbox or len(t.bbox) != 4:
            main_panel.append(t)
            continue

        x1, y1, x2, y2 = t.bbox
        # Header detection: top 11% of full screen (tabs, address bar, bookmarks bar)
        if y2 <= height * 0.11:
            header.append(t)
        # Sidebar detection: leftmost 22% of full screen
        elif x2 <= width * 0.22 and (x2 - x1) < width * 0.3:
            sidebar.append(t)
        else:
            main_panel.append(t)

    return main_panel, sidebar, header

def check_label_value_proximity(
    tokens: List[OCRToken],
    label_pattern: str,
    val_pattern: str,
    width: int,
    height: int,
    fallback_text: str = "",
    max_dist: float = 0.50,
) -> bool:
    """
    Checks if a label token (e.g., 'cpu') is physically close to a value token (e.g., '%')
    in 2D normalized coordinate space or text.
    """
    # Check if a single token contains both
    for t in tokens:
        txt = t.text.lower()
        if re.search(label_pattern, txt) and re.search(val_pattern, txt):
            return True

    # If image is a cropped widget or small card (width < 800 or height < 500),
    # the entire image is a single card. Co-occurrence in the card satisfies label-value relationship.
    if width < 800 or height < 500 or not tokens:
        full_text = fallback_text or " ".join(t.text for t in tokens).lower()
        has_lbl = bool(re.search(label_pattern, full_text))
        has_val = bool(re.search(val_pattern, full_text))
        return has_lbl and has_val

    # On a full dashboard page with multiple widgets, check 2D bounding box proximity
    label_locs = []
    val_locs = []

    for t in tokens:
        if not t.bbox or len(t.bbox) != 4:
            continue
        cx = ((t.bbox[0] + t.bbox[2]) / 2.0) / width
        cy = ((t.bbox[1] + t.bbox[3]) / 2.0) / height
        txt = t.text.lower()
        if re.search(label_pattern, txt):
            label_locs.append((cx, cy))
        if re.search(val_pattern, txt):
            val_locs.append((cx, cy))

    for lx, ly in label_locs:
        for vx, vy in val_locs:
            if abs(lx - vx) <= 0.35 and abs(ly - vy) <= 0.35:
                return True

    return False
