"""
Appendix Caption Normalizer.

Converts historical PM report appendix captions/titles into canonical semantic categories.
Provides template-aware ground-truth resolution separating:
- source_appendix_number: slot where screenshot appeared in historical report
- semantic_category: what PM content is actually evidenced in the screenshot
- canonical_target_appendix: where the category belongs in our standardized PM report
"""

import re
from enum import Enum
from typing import Dict, Optional, Any, List

class GroundTruthSource(str, Enum):
    CAPTION = "CAPTION"
    VERIFIED_CANONICAL_TEMPLATE = "VERIFIED_CANONICAL_TEMPLATE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    MANUAL_ADJUDICATION = "MANUAL_ADJUDICATION"
    UNRESOLVED = "UNRESOLVED"

class ContentStatus(str, Enum):
    CONTENT_MATCH = "CONTENT_MATCH"
    SOURCE_SLOT_SHIFT = "SOURCE_SLOT_SHIFT"
    SOURCE_CONTENT_MISFILED = "SOURCE_CONTENT_MISFILED"
    MULTI_CATEGORY = "MULTI_CATEGORY"
    OCR_UNRESOLVED = "OCR_UNRESOLVED"
    GROUND_TRUTH_UNRESOLVED = "GROUND_TRUTH_UNRESOLVED"

CANONICAL_APPENDIX_TO_CATEGORY: Dict[int, str] = {
    1: "cpu_usage",
    2: "memory_usage",
    3: "interface",
    4: "license_info",
    5: "firmware_version",
    6: "vpn_tunnels",
    7: "routing_table",
    8: "system_uptime",
    9: "gui_access",
    10: "cli_access",
    11: "signature_version",
    12: "firewall_datetime",
    13: "ha_status",
    14: "system_event",
    15: "log_manager",
    16: "backup_configuration",
}

CANONICAL_CATEGORY_TO_APPENDIX: Dict[str, int] = {
    cat: num for num, cat in CANONICAL_APPENDIX_TO_CATEGORY.items()
}

# Normalization mapping rules: normalized string -> canonical semantic category
# Rules are checked in order; exact matches and normalized variants are supported.
CAPTION_MAPPINGS: List[Tuple[str, str]] = [
    # 1. CPU Usage
    ("cpu usage", "cpu_usage"),
    ("cpu utilization", "cpu_usage"),
    ("processor usage", "cpu_usage"),
    ("processor utilization", "cpu_usage"),
    ("cpu", "cpu_usage"),

    # 2. Memory Usage
    ("memory usage", "memory_usage"),
    ("memory utilization", "memory_usage"),
    ("ram usage", "memory_usage"),
    ("ram utilization", "memory_usage"),
    ("memory", "memory_usage"),

    # 3. Interface
    ("interface", "interface"),
    ("interfaces", "interface"),
    ("physical interface status", "interface"),
    ("physical interface", "interface"),
    ("physical interfaces", "interface"),
    ("interface status", "interface"),
    ("network interface", "interface"),
    ("network interfaces", "interface"),

    # 4. License Info
    ("license info", "license_info"),
    ("license information", "license_info"),
    ("fortiguard licensing", "license_info"),
    ("fortiguard license", "license_info"),
    ("forticare license", "license_info"),
    ("forticare licensing", "license_info"),
    ("licensing", "license_info"),
    ("license", "license_info"),

    # 5. Firmware Version
    ("firmware version", "firmware_version"),
    ("firmware", "firmware_version"),
    ("fortios version", "firmware_version"),
    ("os version", "firmware_version"),

    # 6. VPN Tunnels
    ("vpn tunnels", "vpn_tunnels"),
    ("vpn tunnel", "vpn_tunnels"),
    ("ipsec vpn", "vpn_tunnels"),
    ("ipsec vpn tunnels", "vpn_tunnels"),
    ("ipsec vpn tunnel", "vpn_tunnels"),
    ("vpn", "vpn_tunnels"),

    # 7. Routing Table
    ("static routes and routing table", "routing_table"),
    ("static route and routing table", "routing_table"),
    ("static routes and routing", "routing_table"),
    ("static route and routing", "routing_table"),
    ("routing table", "routing_table"),
    ("static routes", "routing_table"),
    ("static route", "routing_table"),
    ("routing", "routing_table"),

    # 8. System Uptime
    ("system uptime", "system_uptime"),
    ("firewall system uptime", "system_uptime"),
    ("firewall uptime", "system_uptime"),
    ("uptime", "system_uptime"),

    # 9. GUI Access
    ("accessed via gui", "gui_access"),
    ("gui access", "gui_access"),
    ("web gui access", "gui_access"),
    ("web gui", "gui_access"),
    ("gui login", "gui_access"),
    ("gui", "gui_access"),

    # 10. CLI Access (includes historical Internet Access CLI ping test)
    ("accessed via cli ssh", "cli_access"),
    ("accessed via cli", "cli_access"),
    ("accessed via ssh", "cli_access"),
    ("cli ssh access", "cli_access"),
    ("cli access", "cli_access"),
    ("ssh access", "cli_access"),
    ("firewall internet access", "cli_access"),
    ("internet access", "cli_access"),
    ("cli", "cli_access"),
    ("ssh", "cli_access"),

    # 11. Signature Version
    ("signatures version", "signature_version"),
    ("signature version", "signature_version"),
    ("definitions", "signature_version"),
    ("signature definitions", "signature_version"),
    ("av ips signatures", "signature_version"),
    ("signatures", "signature_version"),

    # 12. Firewall Date & Time
    ("firewall date and time", "firewall_datetime"),
    ("system date and time", "firewall_datetime"),
    ("date and time", "firewall_datetime"),
    ("firewall datetime", "firewall_datetime"),
    ("system datetime", "firewall_datetime"),
    ("datetime", "firewall_datetime"),

    # 13. HA Status
    ("ha status", "ha_status"),
    ("high availability status", "ha_status"),
    ("high availability", "ha_status"),
    ("ha", "ha_status"),

    # 14. System Event
    ("system event", "system_event"),
    ("system events", "system_event"),
    ("event logs", "system_event"),
    ("event log", "system_event"),
    ("system event logs", "system_event"),
    ("system event log", "system_event"),

    # 15. Log Manager
    ("log manager setting", "log_manager"),
    ("log manager settings", "log_manager"),
    ("log settings", "log_manager"),
    ("log setting", "log_manager"),
    ("logging settings", "log_manager"),
    ("logging setting", "log_manager"),
    ("log manager", "log_manager"),

    # 16. Backup Configuration
    ("backup configuration", "backup_configuration"),
    ("configuration backup", "backup_configuration"),
    ("backup config", "backup_configuration"),
    ("config backup", "backup_configuration"),
    ("backup", "backup_configuration"),
]

def clean_caption_text(caption: str) -> str:
    """
    Cleans raw caption text:
    - strips Appendix numbering prefixes (e.g., 'Appendix 1:', 'Appendix 02 -')
    - lowercases
    - normalizes '&' to 'and'
    - strips punctuation and extra whitespace
    """
    if not caption:
        return ""
    text = caption.strip()
    # Strip appendix prefix like 'Appendix 1 -', 'Appendix 02:', 'Appendix 16'
    text = re.sub(r"(?i)^\s*appendix\s*\d+\s*[\:\-\–\—\.]*\s*", "", text)
    # Lowercase
    text = text.lower()
    # Replace '&' with 'and'
    text = text.replace("&", " and ")
    # Replace '/' with ' '
    text = text.replace("/", " ")
    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_appendix_caption(caption: Optional[str]) -> Optional[str]:
    """
    Converts appendix captions/titles into canonical semantic categories.
    Returns canonical semantic category string, or None if unrecognized.
    """
    if not caption:
        return None

    cleaned = clean_caption_text(caption)
    if not cleaned:
        return None

    # Check exact phrase matches first
    for phrase, category in CAPTION_MAPPINGS:
        if cleaned == phrase:
            return category

    # Check prefix / containment matches for robust handling
    for phrase, category in CAPTION_MAPPINGS:
        # Match whole words within cleaned string
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, cleaned):
            return category

    return None

def resolve_appendix_ground_truth(
    source_appendix_number: int,
    source_caption: Optional[str] = None,
    template_variant: Optional[str] = None,
    is_verified_canonical: bool = False,
    manual_category_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Derives semantic ground truth from caption and template context.
    
    Returns:
    {
        "source_appendix_number": int,
        "source_caption": str or None,
        "semantic_category": str,
        "canonical_target_appendix": int or None,
        "ground_truth_source": GroundTruthSource,
        "is_source_slot_canonical": bool,
    }
    """
    # 1. Manual review override
    if manual_category_override:
        semantic = manual_category_override
        target_app = CANONICAL_CATEGORY_TO_APPENDIX.get(semantic)
        return {
            "source_appendix_number": source_appendix_number,
            "source_caption": source_caption,
            "semantic_category": semantic,
            "canonical_target_appendix": target_app,
            "ground_truth_source": GroundTruthSource.MANUAL_REVIEW.value,
            "is_source_slot_canonical": (source_appendix_number == target_app) if target_app else False,
        }

    # 2. Caption-based derivation
    semantic = normalize_appendix_caption(source_caption)
    if semantic is not None:
        target_app = CANONICAL_CATEGORY_TO_APPENDIX.get(semantic)
        return {
            "source_appendix_number": source_appendix_number,
            "source_caption": source_caption,
            "semantic_category": semantic,
            "canonical_target_appendix": target_app,
            "ground_truth_source": GroundTruthSource.CAPTION.value,
            "is_source_slot_canonical": (source_appendix_number == target_app) if target_app else False,
        }

    # 3. Verified canonical template fallback
    if is_verified_canonical and source_appendix_number in CANONICAL_APPENDIX_TO_CATEGORY:
        semantic = CANONICAL_APPENDIX_TO_CATEGORY[source_appendix_number]
        return {
            "source_appendix_number": source_appendix_number,
            "source_caption": source_caption,
            "semantic_category": semantic,
            "canonical_target_appendix": source_appendix_number,
            "ground_truth_source": GroundTruthSource.VERIFIED_CANONICAL_TEMPLATE.value,
            "is_source_slot_canonical": True,
        }

    # 4. Unresolved
    return {
        "source_appendix_number": source_appendix_number,
        "source_caption": source_caption,
        "semantic_category": "unresolved",
        "canonical_target_appendix": None,
        "ground_truth_source": GroundTruthSource.UNRESOLVED.value,
        "is_source_slot_canonical": False,
    }

# Explicit adjudication registry for development pool ground-truth
ADJUDICATED_DEVELOPMENT_CASES: Dict[tuple, Dict[str, Any]] = {
    ("2ade8e6a79", "appendix_08_uptime.png"): {
        "visible_semantic_categories": ["routing_table"],
        "canonical_target_appendices": [7],
        "source_content_status": ContentStatus.SOURCE_CONTENT_MISFILED.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "HUMAN_SOURCE_MISFILE",
        "rationale": "Historical author pasted Static Route table under Firewall System Uptime caption.",
    },
    ("2ade8e6a79", "appendix_16_04.png"): {
        "visible_semantic_categories": ["system_event"],
        "canonical_target_appendices": [14],
        "source_content_status": ContentStatus.SOURCE_CONTENT_MISFILED.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "HUMAN_SOURCE_MISFILE",
        "rationale": "Historical author pasted Security Events / Threat Weight under Log Manager Setting caption.",
    },
    ("2ade8e6a79", "appendix_16_05.png"): {
        "visible_semantic_categories": ["system_event"],
        "canonical_target_appendices": [14],
        "source_content_status": ContentStatus.SOURCE_CONTENT_MISFILED.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "HUMAN_SOURCE_MISFILE",
        "rationale": "Historical author pasted Threat Weight table under Log Manager Setting caption.",
    },
    ("0af21816cc", "appendix_15_log_manager.png"): {
        "visible_semantic_categories": ["log_manager"],
        "canonical_target_appendices": [15],
        "source_content_status": ContentStatus.SOURCE_CONTENT_MISFILED.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "HUMAN_SOURCE_MISFILE",
        "rationale": "Historical author pasted Summary Logs (Log Manager) under System Event caption.",
    },
    ("0af21816cc", "appendix_14_event.png"): {
        "visible_semantic_categories": ["ha_status"],
        "canonical_target_appendices": [13],
        "source_content_status": ContentStatus.OCR_UNRESOLVED.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "OCR_UNRESOLVED",
        "rationale": "Severe OCR degradation ('H igh Lity Moe') on HA Mode Standalone screenshot.",
    },
    ("0387ca989c", "appendix_05_firmware.png"): {
        "visible_semantic_categories": ["firmware_version", "system_uptime", "firewall_datetime"],
        "canonical_target_appendices": [5, 8, 12],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "VALID_MULTI_CATEGORY",
        "rationale": "System Information widget with co-located Firmware, Uptime, and Date/Time.",
    },
    ("063a90e14a", "appendix_08_uptime.png"): {
        "visible_semantic_categories": ["system_uptime", "firmware_version", "firewall_datetime"],
        "canonical_target_appendices": [8, 5, 12],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "VALID_MULTI_CATEGORY",
        "rationale": "System Information widget with co-located Uptime, Firmware, and Date/Time.",
    },
    ("0af21816cc", "appendix_08_uptime.png"): {
        "visible_semantic_categories": ["system_uptime", "firmware_version", "firewall_datetime"],
        "canonical_target_appendices": [8, 5, 12],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "VALID_MULTI_CATEGORY",
        "rationale": "System Information widget with co-located Uptime, Firmware, and Date/Time.",
    },
    ("0af21816cc", "appendix_12_01.png"): {
        "visible_semantic_categories": ["firewall_datetime", "firmware_version", "system_uptime"],
        "canonical_target_appendices": [12, 5, 8],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "VALID_MULTI_CATEGORY",
        "rationale": "System Information widget with co-located Date/Time, Firmware, and Uptime.",
    },
    ("2ade8e6a79", "appendix_10_01.png"): {
        "visible_semantic_categories": ["cli_access", "ha_status", "signature_version", "system_uptime"],
        "canonical_target_appendices": [10, 13, 11, 8],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "VALID_MULTI_CATEGORY",
        "rationale": "CLI get system status output containing HA status, Signature version, and CLI session.",
    },
    ("b1cf0925e5", "appendix_01_cpu.png"): {
        "visible_semantic_categories": ["cpu_usage", "memory_usage", "gui_access"],
        "canonical_target_appendices": [1, 2, 9],
        "source_content_status": ContentStatus.MULTI_CATEGORY.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "TRUE_CLASSIFIER_ERROR",
        "rationale": "CPU graph embedded in GUI container; resolver preferred gui_access over cpu_usage in single-primary selection.",
    },
    ("2ade8e6a79", "appendix_16_02.png"): {
        "visible_semantic_categories": ["log_manager"],
        "canonical_target_appendices": [15],
        "source_content_status": ContentStatus.SOURCE_SLOT_SHIFT.value,
        "ground_truth_source": GroundTruthSource.MANUAL_ADJUDICATION.value,
        "adjudication_type": "TRUE_CLASSIFIER_ERROR",
        "rationale": "Local Log Settings tab classified as system_event due to event navigation text.",
    },
}

def adjudicate_screenshot(
    case_id: str,
    image_id: str,
    source_appendix_number: int,
    source_caption: Optional[str] = None,
    is_verified_canonical: bool = False,
    manual_category_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Formalizes the four distinct concepts for any screenshot:
    A. source_appendix_number: physical position in historical report
    B. source_caption_category: category implied by historical report caption
    C. visible_semantic_categories: categories actually evidenced in screenshot content
    D. canonical_target_appendices: locations where the evidence belongs in our standardized report
    """
    # Caption-derived category
    caption_cat = normalize_appendix_caption(source_caption)
    if not caption_cat and is_verified_canonical and source_appendix_number in CANONICAL_APPENDIX_TO_CATEGORY:
        caption_cat = CANONICAL_APPENDIX_TO_CATEGORY[source_appendix_number]

    # Check explicit adjudication registry first
    for (cid_sub, img_name), adj_info in ADJUDICATED_DEVELOPMENT_CASES.items():
        if cid_sub in case_id and img_name == image_id:
            return {
                "case_id": case_id,
                "image_id": image_id,
                "source_appendix_number": source_appendix_number,
                "source_caption_category": caption_cat,
                "visible_semantic_categories": adj_info["visible_semantic_categories"],
                "canonical_target_appendices": adj_info["canonical_target_appendices"],
                "source_content_status": adj_info["source_content_status"],
                "ground_truth_source": adj_info["ground_truth_source"],
                "adjudication_type": adj_info.get("adjudication_type"),
                "rationale": adj_info.get("rationale"),
            }

    # If manual category override provided
    if manual_category_override:
        target_app = CANONICAL_CATEGORY_TO_APPENDIX.get(manual_category_override)
        return {
            "case_id": case_id,
            "image_id": image_id,
            "source_appendix_number": source_appendix_number,
            "source_caption_category": caption_cat or manual_category_override,
            "visible_semantic_categories": [manual_category_override],
            "canonical_target_appendices": [target_app] if target_app else [],
            "source_content_status": ContentStatus.SOURCE_SLOT_SHIFT.value if (target_app and target_app != source_appendix_number) else ContentStatus.CONTENT_MATCH.value,
            "ground_truth_source": GroundTruthSource.MANUAL_REVIEW.value,
            "adjudication_type": None,
            "rationale": "Manual review override applied.",
        }

    # Normal caption-based derivation
    if caption_cat:
        target_app = CANONICAL_CATEGORY_TO_APPENDIX.get(caption_cat)
        target_apps = [target_app] if target_app else []
        is_match = (source_appendix_number == target_app) if target_app else False
        content_status = ContentStatus.CONTENT_MATCH.value if is_match else ContentStatus.SOURCE_SLOT_SHIFT.value
        gt_source = GroundTruthSource.VERIFIED_CANONICAL_TEMPLATE.value if (is_verified_canonical and is_match) else GroundTruthSource.CAPTION.value

        return {
            "case_id": case_id,
            "image_id": image_id,
            "source_appendix_number": source_appendix_number,
            "source_caption_category": caption_cat,
            "visible_semantic_categories": [caption_cat],
            "canonical_target_appendices": target_apps,
            "source_content_status": content_status,
            "ground_truth_source": gt_source,
            "adjudication_type": None,
            "rationale": "Derived from historical appendix caption/template.",
        }

    # Fallback to unresolved
    return {
        "case_id": case_id,
        "image_id": image_id,
        "source_appendix_number": source_appendix_number,
        "source_caption_category": None,
        "visible_semantic_categories": [],
        "canonical_target_appendices": [],
        "source_content_status": ContentStatus.GROUND_TRUTH_UNRESOLVED.value,
        "ground_truth_source": GroundTruthSource.UNRESOLVED.value,
        "adjudication_type": None,
        "rationale": "Caption could not be normalized and no manual adjudication exists.",
    }
