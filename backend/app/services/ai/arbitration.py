"""
Arbitration logic between deterministic results and Local AI outputs.
Enforces Critical Identity Safety (hostnames, serial numbers),
multi-category evidence resolution, and review status attribution.
"""

from typing import Dict, Any, List, Optional, Tuple
from .schemas import (
    ArbitrationState,
    AIClassificationResponse,
    AIExtractionResponse,
    AmbiguityCheckResult,
)

IDENTITY_FIELDS = {
    "application.hostname",
    "application.serial_primary",
    "application.serial_secondary",
}

def arbitrate_classification(
    deterministic_category: str,
    deterministic_confidence: float,
    assigned_categories: List[str],
    ambiguity: AmbiguityCheckResult,
    ai_result: Optional[AIClassificationResponse],
) -> Tuple[ArbitrationState, List[str], List[str]]:
    """
    Arbitrates screenshot classification between deterministic engine and AI.
    Returns: (state, final_assigned_categories, disagreements)
    """
    if ai_result is None:
        if ambiguity.ambiguous:
            return ArbitrationState.AI_UNAVAILABLE, assigned_categories, ["Ambiguous screenshot; AI unavailable for verification"]
        return ArbitrationState.DETERMINISTIC_ACCEPTED, assigned_categories, []

    ai_evidenced_cats = [c.category for c in ai_result.categories if c.evidenced]
    disagreements = []

    # Check for multi-category co-location (e.g. System Info = Firmware + Uptime)
    if len(ai_evidenced_cats) > 1:
        merged_categories = list(dict.fromkeys(assigned_categories + ai_evidenced_cats))
        return ArbitrationState.MULTI_CATEGORY, merged_categories, []

    # Single category AI assessment
    if ai_evidenced_cats:
        ai_primary = ai_result.primary_category or ai_evidenced_cats[0]
        if ai_primary == deterministic_category or ai_primary in assigned_categories:
            merged = list(dict.fromkeys(assigned_categories + [ai_primary]))
            return ArbitrationState.AI_VERIFIED, merged, []
        else:
            disagreements.append(
                f"Deterministic predicted '{deterministic_category}', but Local AI identified '{ai_primary}'"
            )
            # Both categories retained in assigned list so neither evidence is dropped
            merged = list(dict.fromkeys(assigned_categories + [ai_primary]))
            return ArbitrationState.DISAGREEMENT, merged, disagreements

    # AI found no categories
    if deterministic_confidence >= 0.85:
        return ArbitrationState.DETERMINISTIC_ACCEPTED, assigned_categories, []
    
    return ArbitrationState.REVIEW_REQUIRED, assigned_categories, ["AI detected no clear evidence for candidate categories"]

def arbitrate_extraction(
    field_path: str,
    deterministic_val: Any,
    deterministic_confidence: float,
    ai_val: Any,
    ai_confidence: float,
) -> Tuple[ArbitrationState, Any, float, List[str]]:
    """
    Arbitrates single-field extraction.
    Enforces that Qwen NEVER silently replaces identity fields on disagreement.
    Returns: (state, final_value, final_confidence, disagreements)
    """
    disagreements = []

    # If no AI value exists
    if ai_val is None:
        if deterministic_val is not None:
            return ArbitrationState.DETERMINISTIC_ACCEPTED, deterministic_val, deterministic_confidence, []
        return ArbitrationState.AI_UNAVAILABLE, None, 0.0, []

    # If deterministic value is missing but AI found one
    if deterministic_val is None:
        if field_path in IDENTITY_FIELDS:
            # Identity field found by AI without OCR confirmation requires review
            return ArbitrationState.REVIEW_REQUIRED, ai_val, ai_confidence, [f"Identity field '{field_path}' extracted by AI without deterministic baseline"]
        return ArbitrationState.AI_VERIFIED, ai_val, ai_confidence, []

    # Both values present: check agreement
    is_agreement = (str(deterministic_val).strip().lower() == str(ai_val).strip().lower())
    if is_agreement:
        return ArbitrationState.AI_VERIFIED, deterministic_val, max(deterministic_confidence, ai_confidence), []

    # DISAGREEMENT
    disagreements.append(
        f"Value conflict on '{field_path}': Deterministic='{deterministic_val}' vs AI='{ai_val}'"
    )

    if field_path in IDENTITY_FIELDS:
        # Section 20: Qwen must NEVER silently replace OCR values for identity fields
        # Keep deterministic value, mark DISAGREEMENT and REVIEW_REQUIRED
        return ArbitrationState.DISAGREEMENT, deterministic_val, deterministic_confidence, disagreements

    # For non-identity telemetry: if AI confidence is significantly higher, suggest AI but flag disagreement
    if ai_confidence > deterministic_confidence + 0.15:
        return ArbitrationState.DISAGREEMENT, ai_val, ai_confidence, disagreements
    else:
        return ArbitrationState.DISAGREEMENT, deterministic_val, deterministic_confidence, disagreements
