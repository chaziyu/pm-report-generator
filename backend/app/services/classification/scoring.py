"""
Scoring utilities for category classification.
Provides backward-compatible scoring functions and term-matching helpers.
"""

import re
from typing import List, Dict, Any
from ...models.screenshot import OCRToken
from .evidence import contains_anchor, match_anchor_groups, match_regex_patterns

def contains_term(text: str, term: str) -> bool:
    """Checks if a term or regex pattern is present in the lowercased text."""
    return contains_anchor(text, term)

def score_category(text_lower: str, tokens: List[OCRToken], profile: Dict[str, Any]) -> float:
    """
    Computes a match score [0.0 - 0.99] for a given category profile against OCR text.
    Maintains backward compatibility with legacy test callers while using V2 semantic structures.
    """
    strong_anchors = profile.get("strong_anchors", profile.get("required_any", []))
    strong_groups = profile.get("strong_groups", [])
    supporting = profile.get("supporting_anchors", profile.get("supporting", []))
    negative = profile.get("negative_anchors", profile.get("negative", []))
    regex_patterns = profile.get("regex_patterns", [])

    base_weight = profile.get("base_weight", 0.65)
    supp_weight = profile.get("supporting_weight", 0.12)
    neg_penalty = profile.get("negative_penalty", 0.25)

    # 1. Check strong anchors / groups
    matched_strong = any(contains_anchor(text_lower, sa) for sa in strong_anchors)
    matched_groups = len(match_anchor_groups(text_lower, strong_groups)) > 0 if strong_groups else False
    matched_regex = len(match_regex_patterns(text_lower, regex_patterns)) > 0 if regex_patterns else False

    if not (matched_strong or matched_groups or matched_regex):
        # Check if supporting terms match without strong anchor
        supp_count = sum(1 for s in supporting if contains_anchor(text_lower, s))
        if supp_count >= 2:
            score = 0.50 + min(0.20, supp_count * 0.05)
        else:
            return 0.0
    else:
        score = base_weight
        if matched_groups:
            score += 0.10
        if matched_regex:
            score += 0.08

        # 2. Add supporting terms
        for s in supporting:
            if contains_anchor(text_lower, s):
                score += supp_weight
                if score >= 0.95:
                    break

    # 3. Negative penalty
    for neg in negative:
        if contains_anchor(text_lower, neg):
            score -= neg_penalty

    return max(0.0, min(0.99, round(score, 3)))
