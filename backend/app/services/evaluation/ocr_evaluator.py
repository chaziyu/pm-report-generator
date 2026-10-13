"""
OCR Evaluator for PM Report evaluation.
Measures whether expected category anchors are detected in OCR output
without leaking customer-sensitive text.
"""

from typing import Dict, List, Any, Tuple
from pathlib import Path
from ...models.screenshot import OCRToken

CATEGORY_ANCHORS: Dict[str, List[str]] = {
    "cpu_usage": ["cpu", "current usage"],
    "memory_usage": ["memory", "current usage"],
    "interface": ["interface", "interfaces", "port"],
    "license_info": ["license", "forticare", "antivirus", "ips"],
    "firmware_version": ["firmware", "build", "system information"],
    "vpn_tunnels": ["vpn", "tunnel", "selectors"],
    "routing_table": ["static route", "routing", "gateway"],
    "system_uptime": ["uptime", "system uptime"],
    "gui_access": ["dashboard", "fortigate"],
    "cli_access": ["cli console", "#", "get system"],
    "signature_version": ["fortiguard", "definitions", "signatures"],
    "firewall_datetime": ["system time", "time zone", "ntp"],
    "ha_status": ["ha", "high availability", "primary"],
    "system_event": ["event", "system events", "log"],
    "log_manager": ["log settings", "fortianalyzer", "log manager"],
    "backup_configuration": ["backup", "download", ".conf"],
}

class OCREvaluator:
    """
    Evaluates OCR quality on an image based on detection of expected category anchors.
    """

    def evaluate_tokens(
        self,
        tokens: List[OCRToken],
        ocr_text: str,
        expected_category: str
    ) -> Dict[str, Any]:
        """
        Safely evaluates OCR tokens against expected category anchors.
        Does not expose raw OCR text or tokens.
        """
        text_lower = ocr_text.lower()
        anchors = CATEGORY_ANCHORS.get(expected_category, [])
        found_anchors = []
        missing_anchors = []

        for anchor in anchors:
            if anchor.lower() in text_lower:
                found_anchors.append(anchor)
            else:
                missing_anchors.append(anchor)

        # Average token confidence if available
        avg_confidence = (
            sum(t.confidence for t in tokens) / len(tokens)
            if tokens else 0.0
        )

        return {
            "token_count": len(tokens),
            "avg_confidence": round(avg_confidence, 4),
            "expected_anchors": anchors,
            "found_anchors": found_anchors,
            "missing_anchors": missing_anchors,
            "all_anchors_detected": len(missing_anchors) == 0,
            "any_anchor_detected": len(found_anchors) > 0,
        }

ocr_evaluator = OCREvaluator()
