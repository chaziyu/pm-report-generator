"""
HTTP Provider communicating with the locally bound llama-server instance (127.0.0.1).
Sends prompts formatted for Qwen3-1.7B Instruct and validates structured JSON responses.
"""

import json
import re
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Callable

from .base import BaseAIProvider
from .schemas import (
    AIClassificationResponse,
    AICategoryEvidence,
    AIExtractionResponse,
    AIExtractedField,
)
from .prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
    ALLOWED_CATEGORIES,
)

def clean_json_text(text: str) -> str:
    """Strips markdown code fencing, <think> tags, and extraneous wrapper text from model output."""
    t = text.strip()
    # Strip <think>...</think> tags if present
    t = re.sub(r"<think>[\s\S]*?</think>", "", t, flags=re.IGNORECASE).strip()
    # Match ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
    # Extract outermost JSON object { ... }
    m2 = re.search(r"(\{[\s\S]*\})", t)
    if m2:
        return m2.group(1).strip()
    return t

class LlamaServerProvider(BaseAIProvider):
    def __init__(self, base_url_provider, request_timeout: float = 90.0, activity_callback: Optional[Callable[[], None]] = None):
        # base_url_provider can be a string or a callable returning str
        self._base_url_provider = base_url_provider
        self.request_timeout = request_timeout
        self.activity_callback = activity_callback
        self.last_response_meta: Dict[str, Any] = {}

    def _get_base_url(self) -> str:
        if callable(self._base_url_provider):
            url = self._base_url_provider()
            if not url:
                raise RuntimeError("llama-server is not running or has no valid base URL")
            return url
        return self._base_url_provider

    def _post_chat(self, system_prompt: str, user_prompt: str) -> str:
        if self.activity_callback:
            try:
                self.activity_callback()
            except Exception:
                pass
        base_url = self._get_base_url()
        endpoint = f"{base_url}/v1/chat/completions"

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PMReportGenerator/1.0",
            "Connection": "close",
        }

        # Attempt post with 1 retry on connection reset
        last_err = None
        for attempt in range(2):
            try:
                req = urllib.request.Request(endpoint, data=data_bytes, headers=headers)
                with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"llama-server returned HTTP {resp.status}")
                    res_obj = json.loads(resp.read().decode("utf-8"))
                    self.last_response_meta = {
                        "timings": res_obj.get("timings", {}),
                        "usage": res_obj.get("usage", {}),
                    }
                    choices = res_obj.get("choices", [])
                    if not choices:
                        raise ValueError("llama-server returned empty choices list")
                    return choices[0]["message"]["content"]
            except (urllib.error.URLError, ConnectionResetError, OSError) as e:
                last_err = e
                # Wait briefly before retry if first attempt failed
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise last_err from None

    def classify(self, ocr_text: str, candidate_categories: List[str]) -> AIClassificationResponse:
        user_prompt = build_classification_prompt(ocr_text, candidate_categories)
        raw_text = self._post_chat(CLASSIFICATION_SYSTEM_PROMPT, user_prompt)
        clean_text = clean_json_text(raw_text)

        parsed = json.loads(clean_text)
        categories_data = parsed.get("categories", [])
        validated_categories: List[AICategoryEvidence] = []

        for item in categories_data:
            cat_name = item.get("category")
            if cat_name in ALLOWED_CATEGORIES and item.get("evidenced", False):
                validated_categories.append(
                    AICategoryEvidence(
                        category=cat_name,
                        evidenced=True,
                        confidence=float(item.get("confidence", 0.90)),
                        reason=item.get("reason"),
                    )
                )

        primary = parsed.get("primary_category")
        if primary not in ALLOWED_CATEGORIES:
            primary = validated_categories[0].category if validated_categories else None

        is_multi = parsed.get("is_multi_category", len(validated_categories) > 1)

        return AIClassificationResponse(
            categories=validated_categories,
            primary_category=primary,
            is_multi_category=is_multi,
            raw_response=raw_text,
        )

    def extract(self, ocr_text: str, requested_fields: List[str]) -> AIExtractionResponse:
        user_prompt = build_extraction_prompt(ocr_text, requested_fields)
        raw_text = self._post_chat(EXTRACTION_SYSTEM_PROMPT, user_prompt)
        clean_text = clean_json_text(raw_text)

        parsed = json.loads(clean_text)
        fields_data = parsed.get("fields", {})
        validated_fields: Dict[str, AIExtractedField] = {}

        for f_name, f_val in fields_data.items():
            if isinstance(f_val, dict):
                validated_fields[f_name] = AIExtractedField(
                    field_path=f_name,
                    value=f_val.get("value"),
                    confidence=float(f_val.get("confidence", 0.90)),
                    source_evidence=f_val.get("source_evidence"),
                )
            else:
                validated_fields[f_name] = AIExtractedField(
                    field_path=f_name,
                    value=f_val,
                    confidence=0.90,
                )

        return AIExtractionResponse(
            fields=validated_fields,
            raw_response=raw_text,
        )
