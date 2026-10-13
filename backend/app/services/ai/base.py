"""
Abstract base class and mock providers for Local AI inference.
Allows testing without the full 1.28 GB GGUF model and llama-server binary.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json

from .schemas import (
    AIClassificationResponse,
    AICategoryEvidence,
    AIExtractionResponse,
    AIExtractedField,
)

class BaseAIProvider(ABC):
    @abstractmethod
    def classify(self, ocr_text: str, candidate_categories: List[str]) -> AIClassificationResponse:
        """Invokes model to determine evidenced categories."""
        pass

    @abstractmethod
    def extract(self, ocr_text: str, requested_fields: List[str]) -> AIExtractionResponse:
        """Invokes model to extract targeted telemetry values."""
        pass

class FakeAIProvider(BaseAIProvider):
    """
    Mock AI Provider for fast, offline, deterministic testing.
    Can be configured to return specific responses, simulate timeouts, or produce invalid JSON.
    """

    def __init__(
        self,
        custom_classification: Optional[AIClassificationResponse] = None,
        custom_extraction: Optional[AIExtractionResponse] = None,
        should_fail: bool = False,
        should_timeout: bool = False,
        return_malformed_json: bool = False,
    ):
        self.custom_classification = custom_classification
        self.custom_extraction = custom_extraction
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.return_malformed_json = return_malformed_json
        self.call_count = 0

    def classify(self, ocr_text: str, candidate_categories: List[str]) -> AIClassificationResponse:
        self.call_count += 1
        if self.should_timeout:
            raise TimeoutError("Simulated FakeAIProvider timeout")
        if self.should_fail:
            raise RuntimeError("Simulated FakeAIProvider server crash")
        if self.return_malformed_json:
            raise json.JSONDecodeError("Invalid JSON from LLM", "{broken_json:", 0)

        if self.custom_classification:
            return self.custom_classification

        # Default intelligent mock behavior based on OCR keywords
        text_lower = ocr_text.lower()
        evidenced: List[AICategoryEvidence] = []

        if "firmware" in text_lower or "build" in text_lower:
            evidenced.append(AICategoryEvidence(category="firmware_version", evidenced=True, confidence=0.96))
        if "uptime" in text_lower or "51d" in text_lower or "177d" in text_lower or "day" in text_lower:
            evidenced.append(AICategoryEvidence(category="system_uptime", evidenced=True, confidence=0.95))
        if "cpu" in text_lower:
            evidenced.append(AICategoryEvidence(category="cpu_usage", evidenced=True, confidence=0.97))
        if "memory" in text_lower:
            evidenced.append(AICategoryEvidence(category="memory_usage", evidenced=True, confidence=0.96))
        if "dashboard" in text_lower or "+ add widget" in text_lower:
            evidenced.append(AICategoryEvidence(category="gui_access", evidenced=True, confidence=0.95))

        is_multi = len(evidenced) > 1
        primary = evidenced[0].category if evidenced else (candidate_categories[0] if candidate_categories else "unknown")

        return AIClassificationResponse(
            categories=evidenced,
            primary_category=primary,
            is_multi_category=is_multi,
            raw_response="[FakeAIProvider mock response]",
        )

    def extract(self, ocr_text: str, requested_fields: List[str]) -> AIExtractionResponse:
        self.call_count += 1
        if self.should_timeout:
            raise TimeoutError("Simulated FakeAIProvider timeout")
        if self.should_fail:
            raise RuntimeError("Simulated FakeAIProvider server crash")

        if self.custom_extraction:
            return self.custom_extraction

        fields: Dict[str, AIExtractedField] = {}
        text_lower = ocr_text.lower()

        for field in requested_fields:
            if field == "hardware.cpu_usage" and "0%" in text_lower:
                fields[field] = AIExtractedField(field_path=field, value=0, confidence=0.98)
            elif field == "hardware.memory_usage" and "33%" in text_lower:
                fields[field] = AIExtractedField(field_path=field, value=33, confidence=0.98)
            elif field == "hardware.memory_usage" and "55%" in text_lower:
                fields[field] = AIExtractedField(field_path=field, value=55, confidence=0.98)
            elif field == "firmware.current" and "7.4.11" in text_lower:
                fields[field] = AIExtractedField(field_path=field, value="7.4.11", confidence=0.99)
            elif field == "configuration.uptime" and "177 days" in text_lower:
                fields[field] = AIExtractedField(field_path=field, value="177 days 14 hours 24 minutes", confidence=0.97)

        return AIExtractionResponse(fields=fields, raw_response="[FakeAIProvider mock extraction]")
