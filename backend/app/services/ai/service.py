"""
Local AI Service for PM Report Generator.
Coordinates ambiguity detection, lazy llama-server activation,
caching, arbitration, and provenance tracking.
"""

import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ...models.screenshot import ScreenshotRecord
from .schemas import (
    ArbitrationState,
    AIClassificationResponse,
    AIExtractionResponse,
    AmbiguityCheckResult,
    AIProvenance,
)
from .base import BaseAIProvider, FakeAIProvider
from .llama_provider import LlamaServerProvider
from .ambiguity import ambiguity_detector, AmbiguityDetector
from .arbitration import arbitrate_classification, arbitrate_extraction
from .cache import ai_cache, compute_cache_key
from .runtime.manager import LocalAIRuntimeManager
from .model.manager import LocalAIModelManager

class LocalAIService:
    def __init__(
        self,
        runtime_manager: Optional[LocalAIRuntimeManager] = None,
        model_manager: Optional[LocalAIModelManager] = None,
        provider: Optional[BaseAIProvider] = None,
        ambiguity_checker: Optional[AmbiguityDetector] = None,
        enabled: bool = True,
    ):
        self.model_manager = model_manager or LocalAIModelManager()
        self.runtime_manager = runtime_manager or LocalAIRuntimeManager(model_manager=self.model_manager, enabled=enabled)
        self.ambiguity_checker = ambiguity_checker or ambiguity_detector
        self.enabled = enabled

        # If a custom provider (like FakeAIProvider) is supplied, use it;
        # otherwise use LlamaServerProvider backed by runtime_manager
        if provider:
            self._provider = provider
        else:
            self._provider = LlamaServerProvider(
                base_url_provider=lambda: self.runtime_manager.base_url,
                activity_callback=self.runtime_manager._touch_activity,
            )

    def set_provider(self, provider: BaseAIProvider) -> None:
        """Sets or replaces the active AI provider (e.g. for testing)."""
        self._provider = provider

    def get_status(self) -> Dict[str, Any]:
        """Returns consolidated AI status for API and UI consumption."""
        if not self.enabled:
            return {"status": "DISABLED", "message": "Local AI is disabled in configuration"}
        return self.runtime_manager.get_status()

    def check_ambiguity(self, screenshot: ScreenshotRecord) -> AmbiguityCheckResult:
        """Runs the ambiguity detector on the screenshot."""
        return self.ambiguity_checker.detect(screenshot)

    def is_ai_available(self) -> bool:
        if not self.enabled:
            return False
        if isinstance(self._provider, FakeAIProvider):
            return True
        if self.runtime_manager.is_running:
            return True
        status = self.get_status()
        return status.get("status") in ("READY", "READY_BUT_UNLOADED", "RUNNING")

    def verify_classification(
        self,
        screenshot: ScreenshotRecord,
        deterministic_category: str,
        deterministic_confidence: float,
    ) -> Tuple[ArbitrationState, List[str], Optional[AIProvenance]]:
        """
        Evaluates whether AI verification is required for classification,
        lazily invokes Qwen if necessary, and arbitrates the outcome.
        """
        ambiguity = self.check_ambiguity(screenshot)

        # Section 14: AI Invocation Policy
        # IF high confidence (>= 0.85) AND ambiguity detector says clear -> no AI needed
        if deterministic_confidence >= 0.85 and not ambiguity.ambiguous:
            return (
                ArbitrationState.DETERMINISTIC_ACCEPTED,
                screenshot.assigned_categories,
                None,
            )

        # AI is required. Check if runtime/model is available
        if not self.is_ai_available():
            # AI unavailable: fallback to deterministic result
            state, cats, dis = arbitrate_classification(
                deterministic_category=deterministic_category,
                deterministic_confidence=deterministic_confidence,
                assigned_categories=screenshot.assigned_categories,
                ambiguity=ambiguity,
                ai_result=None,
            )
            return state, cats, None

        # Build provenance hashes
        sc_hash = screenshot.sha256 or hashlib.sha256(screenshot.filename.encode()).hexdigest()
        ocr_hash = hashlib.sha256(screenshot.ocr_text.encode("utf-8")).hexdigest()
        manifest = self.model_manager.manifest

        cache_key = compute_cache_key(
            screenshot_hash=sc_hash,
            ocr_text_hash=ocr_hash,
            task_type="classification",
            model_revision=manifest.model_revision,
            prompt_version=manifest.prompt_version,
        )

        t0 = time.perf_counter()
        ai_resp: Optional[AIClassificationResponse] = None

        # Check Cache
        cached_data = ai_cache.get(cache_key)
        if cached_data:
            ai_resp = AIClassificationResponse.parse_obj(cached_data)
        else:
            try:
                # Lazy model startup: ensure server is running
                if not isinstance(self._provider, LlamaServerProvider) or self.runtime_manager.is_running:
                    pass
                else:
                    self.runtime_manager.ensure_server_running()

                # Acquire inference lock (concurrency = 1)
                with self.runtime_manager.acquire_inference_lock():
                    ai_resp = self._provider.classify(
                        ocr_text=screenshot.ocr_text,
                        candidate_categories=ambiguity.candidate_categories,
                    )
                # Store in cache
                ai_cache.set(cache_key, ai_resp.dict())
            except Exception as e:
                # Discard failed AI call, continue deterministic pipeline
                ai_resp = None

        proc_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        state, final_categories, disagreements = arbitrate_classification(
            deterministic_category=deterministic_category,
            deterministic_confidence=deterministic_confidence,
            assigned_categories=screenshot.assigned_categories,
            ambiguity=ambiguity,
            ai_result=ai_resp,
        )

        provenance = AIProvenance(
            model_id=manifest.model_id,
            model_revision=manifest.model_revision,
            prompt_version=manifest.prompt_version,
            input_ocr_hash=ocr_hash,
            screenshot_hash=sc_hash,
            arbitration_state=state,
            processing_time_ms=proc_time_ms,
            deterministic_result={"category": deterministic_category, "confidence": deterministic_confidence},
            ai_result=ai_resp.dict() if ai_resp else None,
            disagreements=disagreements,
        )

        return state, final_categories, provenance

    def verify_extraction(
        self,
        screenshot: ScreenshotRecord,
        field_path: str,
        deterministic_val: Any,
        deterministic_confidence: float,
    ) -> Tuple[ArbitrationState, Any, float, Optional[AIProvenance]]:
        """
        Assists with field extraction verification when deterministic parsing is uncertain.
        Enforces strict identity protection for hostnames and serial numbers.
        """
        # If deterministic result is high confidence, skip AI
        if deterministic_val is not None and deterministic_confidence >= 0.95:
            return (
                ArbitrationState.DETERMINISTIC_ACCEPTED,
                deterministic_val,
                deterministic_confidence,
                None,
            )

        if not self.is_ai_available():
            return (
                ArbitrationState.AI_UNAVAILABLE,
                deterministic_val,
                deterministic_confidence,
                None,
            )

        sc_hash = screenshot.sha256 or hashlib.sha256(screenshot.filename.encode()).hexdigest()
        ocr_hash = hashlib.sha256(screenshot.ocr_text.encode("utf-8")).hexdigest()
        manifest = self.model_manager.manifest

        cache_key = compute_cache_key(
            screenshot_hash=sc_hash,
            ocr_text_hash=ocr_hash,
            task_type=f"extraction:{field_path}",
            model_revision=manifest.model_revision,
            prompt_version=manifest.prompt_version,
        )

        t0 = time.perf_counter()
        ai_resp: Optional[AIExtractionResponse] = None

        cached_data = ai_cache.get(cache_key)
        if cached_data:
            ai_resp = AIExtractionResponse.parse_obj(cached_data)
        else:
            try:
                if isinstance(self._provider, LlamaServerProvider) and not self.runtime_manager.is_running:
                    self.runtime_manager.ensure_server_running()

                with self.runtime_manager.acquire_inference_lock():
                    ai_resp = self._provider.extract(
                        ocr_text=screenshot.ocr_text,
                        requested_fields=[field_path],
                    )
                ai_cache.set(cache_key, ai_resp.dict())
            except Exception:
                ai_resp = None

        proc_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        ai_field = ai_resp.fields.get(field_path) if ai_resp else None
        ai_val = ai_field.value if ai_field else None
        ai_conf = ai_field.confidence if ai_field else 0.0

        state, final_val, final_conf, disagreements = arbitrate_extraction(
            field_path=field_path,
            deterministic_val=deterministic_val,
            deterministic_confidence=deterministic_confidence,
            ai_val=ai_val,
            ai_confidence=ai_conf,
        )

        provenance = AIProvenance(
            model_id=manifest.model_id,
            model_revision=manifest.model_revision,
            prompt_version=manifest.prompt_version,
            input_ocr_hash=ocr_hash,
            screenshot_hash=sc_hash,
            arbitration_state=state,
            processing_time_ms=proc_time_ms,
            deterministic_result={"value": deterministic_val, "confidence": deterministic_confidence},
            ai_result=ai_field.dict() if ai_field else None,
            disagreements=disagreements,
        )

        return state, final_val, final_conf, provenance

local_ai_service = LocalAIService()
