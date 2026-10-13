"""
Classifier V2: Two-Stage Semantic Anchor Classifier
Stage 1: ContentCategoryDetector (Multi-label PM content detection)
Stage 2: AppendixAssignmentResolver (Resolves primary appendix assignment,
         pairwise disambiguation, confidence margin, and review status)
"""

from typing import List, Dict, Any, Optional
from ...models.screenshot import ScreenshotRecord, ClassificationCandidate
from .detector import detector
from .resolver import resolver
from .profiles import CATEGORY_PROFILES
from .scoring import score_category

AUTO_ASSIGN_THRESHOLD = 0.85
REVIEW_REQUIRED_THRESHOLD = 0.65

class ScreenshotClassifier:
    """
    Classifier V2 orchestrates Stage 1 (content detection) and Stage 2 (appendix resolution).
    Preserves auditability, provenance, and backwards compatibility.
    """

    def classify(self, screenshot: ScreenshotRecord) -> ScreenshotRecord:
        # Stage 1: Content Detection
        detected_categories = detector.detect_categories(screenshot)
        screenshot.stage1_categories = {
            cat: det.confidence for cat, det in detected_categories.items()
        }

        # Stage 2: Appendix Assignment Resolution
        candidates, assigned, review_status, reason = resolver.resolve(detected_categories, screenshot)

        screenshot.classification_candidates = candidates
        screenshot.assigned_categories = assigned
        screenshot.review_status = review_status
        screenshot.resolution_reason = reason

        return screenshot

classifier = ScreenshotClassifier()
