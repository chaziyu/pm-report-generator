"""
Pydantic schemas for Local AI responses, arbitration states, and provenance metadata.
Enforces strict structured outputs for classification, extraction verification, and identity protection.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ArbitrationState(str, Enum):
    DETERMINISTIC_ACCEPTED = "DETERMINISTIC_ACCEPTED"
    AI_VERIFIED = "AI_VERIFIED"
    MULTI_CATEGORY = "MULTI_CATEGORY"
    DISAGREEMENT = "DISAGREEMENT"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class AICategoryEvidence(BaseModel):
    category: str
    evidenced: bool
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    reason: Optional[str] = None

class AIClassificationResponse(BaseModel):
    categories: List[AICategoryEvidence] = []
    primary_category: Optional[str] = None
    is_multi_category: bool = False
    raw_response: Optional[str] = None

class AIExtractedField(BaseModel):
    field_path: str
    value: Any
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    source_evidence: Optional[str] = None

class AIExtractionResponse(BaseModel):
    fields: Dict[str, AIExtractedField] = {}
    raw_response: Optional[str] = None

class TriggerCategory(str, Enum):
    HIGH_CONFIDENCE_MULTI_CATEGORY = "HIGH_CONFIDENCE_MULTI_CATEGORY"
    TRUE_LOW_CONFIDENCE = "TRUE_LOW_CONFIDENCE"
    OCR_UNRESOLVED = "OCR_UNRESOLVED"
    PRIMARY_SELECTION_AMBIGUITY = "PRIMARY_SELECTION_AMBIGUITY"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    CLEAR_DETERMINISTIC = "CLEAR_DETERMINISTIC"

class AmbiguityCheckResult(BaseModel):
    ambiguous: bool
    reasons: List[str] = []
    candidate_categories: List[str] = []
    trigger_category: Optional[TriggerCategory] = None

class AIProvenance(BaseModel):
    model_id: str
    model_revision: str
    prompt_version: str
    input_ocr_hash: str
    screenshot_hash: str
    arbitration_state: ArbitrationState
    processing_time_ms: float = 0.0
    deterministic_result: Optional[Dict[str, Any]] = None
    ai_result: Optional[Dict[str, Any]] = None
    disagreements: List[str] = []
