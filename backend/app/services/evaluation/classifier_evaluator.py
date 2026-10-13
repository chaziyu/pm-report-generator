"""
Classifier Evaluator for PM Report evaluation.
Evaluates the production classifier on appendix screenshots using actual OCR tokens/text.
Ensures appendix filenames are not used as classification hints.
"""

from typing import Dict, List, Any, Optional
import time
from pathlib import Path

from ...models.screenshot import ScreenshotRecord, ClassificationCandidate
from ..classification.classifier import classifier
from ..classification.profiles import CATEGORY_PROFILES
from .caption_normalizer import (
    CANONICAL_APPENDIX_TO_CATEGORY,
    CANONICAL_CATEGORY_TO_APPENDIX,
    resolve_appendix_ground_truth,
    GroundTruthSource,
)

# Preserved for backwards compatibility with existing callers
APPENDIX_TO_CATEGORY: Dict[int, str] = CANONICAL_APPENDIX_TO_CATEGORY

class ClassifierEvaluator:
    """
    Evaluates screenshot classification accuracy against ground-truth appendix categories.
    Supports:
    - semantic ground truth derived from historical captions
    - verified canonical template fallback
    - explicit separate metrics for source slot vs semantic content
    """

    def evaluate_screenshot(
        self,
        case_id: str,
        appendix_number: int,
        image_index: int,
        image_filename: str,
        screenshot: ScreenshotRecord,
        expected_category: Optional[str] = None,
        source_caption: Optional[str] = None,
        is_verified_canonical: bool = False,
        manual_category_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs actual classifier on the screenshot and compares against semantic expected category.
        Ensures filename is anonymized during evaluation so no hints leak.
        """
        if expected_category is None:
            resolved = resolve_appendix_ground_truth(
                source_appendix_number=appendix_number,
                source_caption=source_caption,
                is_verified_canonical=is_verified_canonical,
                manual_category_override=manual_category_override,
            )
            expected_category = resolved["semantic_category"]
            canonical_target_appendix = resolved["canonical_target_appendix"]
            ground_truth_source = resolved["ground_truth_source"]
            is_source_slot_canonical = resolved["is_source_slot_canonical"]
        else:
            canonical_target_appendix = CANONICAL_CATEGORY_TO_APPENDIX.get(expected_category)
            ground_truth_source = GroundTruthSource.MANUAL_REVIEW.value if manual_category_override else GroundTruthSource.CAPTION.value
            is_source_slot_canonical = (appendix_number == canonical_target_appendix) if canonical_target_appendix else False

        # Anonymize filename so classifier can never use it as a hint
        original_fn = screenshot.filename
        screenshot.filename = f"IMG_{appendix_number:02d}_{image_index:02d}.png"

        t0 = time.perf_counter()
        classified_record = classifier.classify(screenshot)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Restore original filename for metadata tracking
        screenshot.filename = original_fn

        candidates = classified_record.classification_candidates
        top_candidate = candidates[0] if candidates else None

        predicted_category = top_candidate.category if top_candidate else "unknown"
        confidence = round(top_candidate.confidence, 4) if top_candidate else 0.0

        top_3 = [
            {"category": c.category, "confidence": round(c.confidence, 4)}
            for c in candidates[:3]
        ]

        correct = (predicted_category == expected_category) if expected_category != "unresolved" else False

        return {
            "case_id": case_id,
            "appendix_number": appendix_number,  # backwards compatible
            "source_appendix_number": appendix_number,
            "source_appendix_caption": source_caption,
            "image_index": image_index,
            "image_filename": image_filename,
            "expected_category": expected_category,
            "predicted_category": predicted_category,
            "confidence": confidence,
            "top_3_candidates": top_3,
            "correct": correct,
            "review_status": classified_record.review_status,
            "assigned_categories": classified_record.assigned_categories,
            "in_assigned_categories": (expected_category in classified_record.assigned_categories) if expected_category != "unresolved" else False,
            "canonical_target_appendix": canonical_target_appendix,
            "is_source_slot_canonical": is_source_slot_canonical,
            "ground_truth_source": ground_truth_source,
            "classification_time_ms": duration_ms,
            "processing_time_ms": duration_ms,
        }

classifier_evaluator = ClassifierEvaluator()
