"""
Local AI Subsystem for PM Report Generator.
Provides optional Qwen3-1.7B verification, ambiguity detection,
and strict arbitration over the primary deterministic pipeline.
"""

from .schemas import (
    ArbitrationState,
    AIClassificationResponse,
    AICategoryEvidence,
    AIExtractionResponse,
    AIExtractedField,
    AmbiguityCheckResult,
    AIProvenance,
)
from .base import BaseAIProvider, FakeAIProvider
from .llama_provider import LlamaServerProvider
from .ambiguity import AmbiguityDetector, ambiguity_detector
from .arbitration import arbitrate_classification, arbitrate_extraction
from .cache import LocalAICache, ai_cache
from .service import LocalAIService, local_ai_service

__all__ = [
    "ArbitrationState",
    "AIClassificationResponse",
    "AICategoryEvidence",
    "AIExtractionResponse",
    "AIExtractedField",
    "AmbiguityCheckResult",
    "AIProvenance",
    "BaseAIProvider",
    "FakeAIProvider",
    "LlamaServerProvider",
    "AmbiguityDetector",
    "ambiguity_detector",
    "arbitrate_classification",
    "arbitrate_extraction",
    "LocalAICache",
    "ai_cache",
    "LocalAIService",
    "local_ai_service",
]
