"""
Extraction Evaluator for PM Report evaluation.
Evaluates field extraction and rule engine evaluation against ground-truth expected.json.
Implements field-specific comparison rules and error attribution.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from ...models.pm_data import PMData
from ...models.screenshot import ScreenshotRecord
from ..extraction.extractor import master_extractor
from ..rules.engine import rules_engine

EVALUATED_FIELDS = [
    "application.hostname",
    "application.serial_primary",
    "application.serial_secondary",
    "hardware.cpu_usage",
    "hardware.memory_usage",
    "hardware.active_ports",
    "licensing.expiration_date",
    "firmware.current",
    "firmware.build",
    "firmware.maturity",
    "vpn.total",
    "vpn.active",
    "vpn.inactive",
    "configuration.uptime",
    "configuration.timezone",
]

EVALUATED_RULES = [
    "hardware.cpu_status",
    "hardware.memory_status",
    "firmware.status",
    "configuration.backup_status",
]

# Mapping from field to the appendix numbers that typically provide evidence for it
FIELD_TO_EXPECTED_APPENDICES: Dict[str, List[int]] = {
    "application.hostname": [5, 8, 9, 10],
    "application.serial_primary": [5, 8, 9, 10],
    "application.serial_secondary": [5, 8, 9, 10],
    "hardware.cpu_usage": [1],
    "hardware.memory_usage": [2],
    "hardware.active_ports": [3],
    "licensing.expiration_date": [4],
    "firmware.current": [5],
    "firmware.build": [5],
    "firmware.maturity": [5],
    "vpn.total": [6],
    "vpn.active": [6],
    "vpn.inactive": [6],
    "configuration.uptime": [8, 5],
    "configuration.timezone": [12, 5],
}

def normalize_version(val: Any) -> str:
    """Normalizes firmware version (e.g. 'v7.4.11' -> '7.4.11')."""
    if val is None:
        return ""
    s = str(val).strip()
    return s.lstrip("vV").strip()

def normalize_status(val: Any) -> str:
    """Normalizes status string (e.g. 'Out-of-Date' -> 'out_of_date')."""
    if val is None:
        return ""
    return str(val).strip().lower().replace("-", "_").replace(" ", "_")

def normalize_uptime(val: Any) -> str:
    """Normalizes uptime string to compare elapsed day/hour/minute counts."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    # Extract numbers for days, hours, mins
    m_days = re.search(r"(\d+)\s*day", s)
    m_hours = re.search(r"(\d+)\s*hour", s)
    m_mins = re.search(r"(\d+)\s*min", s)
    d = m_days.group(1) if m_days else "0"
    h = m_hours.group(1) if m_hours else "0"
    m = m_mins.group(1) if m_mins else "0"
    return f"{d}d {h}h {m}m"

def normalize_timezone(val: Any) -> str:
    """Normalizes timezone string (e.g. 'GMT +8' -> 'gmt+8')."""
    if val is None:
        return ""
    return str(val).lower().replace(" ", "")

def compare_field_value(field: str, extracted: Any, expected: Any) -> bool:
    """
    Performs field-specific comparison according to Section 10 rules.
    """
    if expected is None:
        return extracted is None

    if extracted is None:
        return False

    # Exact string
    if field in ("application.hostname", "application.serial_primary", "application.serial_secondary", "firmware.build"):
        return str(extracted).strip() == str(expected).strip()

    # Normalized version
    if field == "firmware.current":
        return normalize_version(extracted) == normalize_version(expected)

    # Numeric exact
    if field in ("hardware.cpu_usage", "hardware.memory_usage", "hardware.active_ports", "vpn.total", "vpn.active", "vpn.inactive"):
        try:
            return int(extracted) == int(expected)
        except (ValueError, TypeError):
            return False

    # Normalized text
    if field == "configuration.uptime":
        return normalize_uptime(extracted) == normalize_uptime(expected)

    if field == "configuration.timezone":
        return normalize_timezone(extracted) == normalize_timezone(expected)

    if field == "firmware.maturity":
        return str(extracted).strip().lower() == str(expected).strip().lower()

    if field == "licensing.expiration_date":
        # DD/MM/YYYY or YYYY-MM-DD
        return str(extracted).strip() == str(expected).strip()

    return str(extracted).strip() == str(expected).strip()

def get_extracted_field_value(pm_data: PMData, field: str) -> Any:
    """Retrieves the extracted value from PMData by dotted field path."""
    if field == "application.hostname":
        return pm_data.application.hostname.value
    if field == "application.serial_primary":
        return pm_data.application.serial_primary.value
    if field == "application.serial_secondary":
        return pm_data.application.serial_secondary.value
    if field == "hardware.cpu_usage":
        return pm_data.hardware.cpu_usage.value
    if field == "hardware.memory_usage":
        return pm_data.hardware.memory_usage.value
    if field == "hardware.active_ports":
        return pm_data.hardware.active_ports.value
    if field == "licensing.expiration_date":
        return pm_data.licensing.expiry_date.value
    if field == "firmware.current":
        return pm_data.firmware.current.value
    if field == "firmware.build":
        return pm_data.firmware.build.value
    if field == "firmware.maturity":
        return pm_data.firmware.maturity.value
    if field == "vpn.total":
        return pm_data.vpn.total.value
    if field == "vpn.active":
        return pm_data.vpn.active.value
    if field == "vpn.inactive":
        return pm_data.vpn.inactive.value
    if field == "configuration.uptime":
        return pm_data.configuration.uptime.value
    if field == "configuration.timezone":
        return pm_data.configuration.timezone.value
    return None

def get_expected_field_value(expected: Dict[str, Any], field: str) -> Any:
    """Retrieves the expected ground truth value from expected.json dict."""
    parts = field.split(".")
    curr = expected
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        else:
            return None
    return curr

def get_rule_values(pm_data: PMData, expected: Dict[str, Any], rule: str) -> Tuple[Any, Any]:
    """Retrieves actual and expected values for a rule status."""
    if rule == "hardware.cpu_status":
        actual = pm_data.hardware.cpu_status.value
        exp = expected.get("hardware", {}).get("cpu_status")
    elif rule == "hardware.memory_status":
        actual = pm_data.hardware.memory_status.value
        exp = expected.get("hardware", {}).get("memory_status")
    elif rule == "firmware.status":
        actual = pm_data.firmware.status.value
        exp = expected.get("firmware", {}).get("status")
    elif rule == "configuration.backup_status":
        actual = pm_data.configuration.backup_status.value
        exp = expected.get("configuration", {}).get("backup_status")
    else:
        actual = None
        exp = None
    return actual, exp

class ExtractionEvaluator:
    """
    Evaluates extraction and rules across all screenshots for a case.
    """

    def evaluate_case(
        self,
        case_id: str,
        screenshots: List[ScreenshotRecord],
        expected: Dict[str, Any],
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs production master_extractor and rules_engine on the case's screenshots.
        Evaluates extracted fields and business rules against expected.json.
        """
        # Run production extraction
        pm_data = PMData()
        pm_data = master_extractor.extract_all(screenshots, pm_data)
        pm_data = rules_engine.evaluate(pm_data)

        # Build map of screenshot id / appendix mappings
        # Find which screenshots belong to which appendix
        app_to_screenshots: Dict[int, List[ScreenshotRecord]] = {}
        for sc in screenshots:
            # sc.id is format like case_id_app_num_idx or similar
            for app_num_str, app_info in manifest.get("appendices", {}).items():
                app_num = int(app_num_str)
                if sc.filename in app_info.get("images", []):
                    app_to_screenshots.setdefault(app_num, []).append(sc)

        field_results: Dict[str, Any] = {}
        for field in EVALUATED_FIELDS:
            exp_val = get_expected_field_value(expected, field)
            if exp_val is None:
                # Do not evaluate fields where expected.json has null
                continue

            act_val = get_extracted_field_value(pm_data, field)
            correct = compare_field_value(field, act_val, exp_val)

            root_cause = None
            if not correct:
                root_cause = self._attribute_error(field, exp_val, act_val, screenshots, app_to_screenshots)

            field_results[field] = {
                "expected": exp_val,
                "extracted": act_val,
                "correct": correct,
                "root_cause": root_cause,
            }

        # Evaluate rules
        rule_results: Dict[str, Any] = {}
        for rule in EVALUATED_RULES:
            actual, exp = get_rule_values(pm_data, expected, rule)
            if exp is None:
                continue
            rule_corr = (normalize_status(actual) == normalize_status(exp))
            rule_results[rule] = {
                "expected": exp,
                "actual": actual,
                "correct": rule_corr,
            }

        return {
            "case_id": case_id,
            "fields": field_results,
            "rules": rule_results,
            "pm_data": pm_data.dict(),
        }

    def _attribute_error(
        self,
        field: str,
        expected_val: Any,
        extracted_val: Any,
        screenshots: List[ScreenshotRecord],
        app_to_screenshots: Dict[int, List[ScreenshotRecord]]
    ) -> str:
        """
        Attributes the root cause of an extraction error according to Section 12.
        """
        if field == "hardware.active_ports":
            # Active ports extraction is not currently implemented in master_extractor
            return "UNSUPPORTED_VARIATION"

        expected_apps = FIELD_TO_EXPECTED_APPENDICES.get(field, [])
        relevant_scs: List[ScreenshotRecord] = []
        for app in expected_apps:
            relevant_scs.extend(app_to_screenshots.get(app, []))

        if not relevant_scs:
            return "UNKNOWN"

        # Check if any relevant screenshot was assigned the required category
        assigned_any = any(len(sc.assigned_categories) > 0 for sc in relevant_scs)
        if not assigned_any:
            return "CLASSIFICATION_ERROR"

        # Check OCR text of relevant screenshots
        expected_str = str(expected_val).strip()
        found_in_ocr = any(expected_str.lower() in sc.ocr_text.lower() for sc in relevant_scs)

        if not found_in_ocr:
            # Value was not recognized by OCR
            return "OCR_ERROR"
        else:
            # Value was in OCR text, but parser failed to extract it properly
            return "EXTRACTION_ERROR"

extraction_evaluator = ExtractionEvaluator()
