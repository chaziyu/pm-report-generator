"""
Evaluation package for PM Report Generator.
Provides evaluation services for OCR, classification, extraction, and end-to-end pipeline.
"""

from .classifier_evaluator import classifier_evaluator, ClassifierEvaluator, APPENDIX_TO_CATEGORY
from .caption_normalizer import (
    normalize_appendix_caption,
    resolve_appendix_ground_truth,
    CANONICAL_APPENDIX_TO_CATEGORY,
    CANONICAL_CATEGORY_TO_APPENDIX,
    GroundTruthSource,
)
from .extraction_evaluator import extraction_evaluator, ExtractionEvaluator, EVALUATED_FIELDS, EVALUATED_RULES
from .ocr_evaluator import ocr_evaluator, OCREvaluator, CATEGORY_ANCHORS
from .pipeline_evaluator import PipelineEvaluator
from .report import generate_markdown_report

__all__ = [
    "classifier_evaluator",
    "ClassifierEvaluator",
    "APPENDIX_TO_CATEGORY",
    "normalize_appendix_caption",
    "resolve_appendix_ground_truth",
    "CANONICAL_APPENDIX_TO_CATEGORY",
    "CANONICAL_CATEGORY_TO_APPENDIX",
    "GroundTruthSource",
    "extraction_evaluator",
    "ExtractionEvaluator",
    "EVALUATED_FIELDS",
    "EVALUATED_RULES",
    "ocr_evaluator",
    "OCREvaluator",
    "CATEGORY_ANCHORS",
    "PipelineEvaluator",
    "generate_markdown_report",
]
