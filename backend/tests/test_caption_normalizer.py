"""
Unit tests for Appendix Caption Normalizer and Template-Aware Semantic Evaluation.
Validates:
- Canonical captions normalization
- Known historical caption variants
- Punctuation, whitespace, case, and prefix handling
- Unrecognized and ambiguous captions -> unresolved
- Non-canonical report order resolution with synthetic fixture
- Evaluator accuracy based on semantic content rather than source appendix numbers
All test data is sanitized without customer or hardware specifics.
"""

import unittest
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.evaluation.caption_normalizer import (
    normalize_appendix_caption,
    resolve_appendix_ground_truth,
    CANONICAL_APPENDIX_TO_CATEGORY,
    CANONICAL_CATEGORY_TO_APPENDIX,
    GroundTruthSource,
)
from app.services.evaluation.classifier_evaluator import classifier_evaluator
from app.models.screenshot import ScreenshotRecord, OCRToken

def make_dummy_screenshot(text: str, filename: str = "img.png") -> ScreenshotRecord:
    tokens = [OCRToken(text=w, bbox=[0, 0, 10, 10], confidence=0.99) for w in text.split()]
    return ScreenshotRecord(
        id="test_sc_01",
        filename=filename,
        original_path=f"dummy/{filename}",
        ocr_text=text,
        ocr_tokens=tokens,
    )

class TestAppendixCaptionNormalizer(unittest.TestCase):
    def test_canonical_captions(self):
        """Standard canonical captions map correctly to their semantic categories."""
        expected_mappings = {
            "CPU Usage": "cpu_usage",
            "Memory Usage": "memory_usage",
            "Interface": "interface",
            "License Info": "license_info",
            "Firmware Version": "firmware_version",
            "VPN Tunnels": "vpn_tunnels",
            "Static Routes & Routing Table": "routing_table",
            "Firewall System Uptime": "system_uptime",
            "Accessed via GUI": "gui_access",
            "Accessed via CLI/SSH": "cli_access",
            "Signatures Version": "signature_version",
            "Firewall Date & Time": "firewall_datetime",
            "HA Status": "ha_status",
            "System Event": "system_event",
            "Log Manager Setting": "log_manager",
            "Backup Configuration": "backup_configuration",
        }
        for caption, expected_cat in expected_mappings.items():
            with self.subTest(caption=caption):
                self.assertEqual(normalize_appendix_caption(caption), expected_cat)

    def test_known_historical_variants(self):
        """Historical report title variations map to correct categories."""
        variants = {
            # CPU
            "CPU Utilization": "cpu_usage",
            "Processor Usage": "cpu_usage",
            "Processor Utilization": "cpu_usage",
            # Memory
            "Memory Utilization": "memory_usage",
            "RAM Usage": "memory_usage",
            # Interface
            "Interfaces": "interface",
            "Physical Interface Status": "interface",
            "Network Interfaces": "interface",
            # License
            "License Information": "license_info",
            "FortiGuard Licensing": "license_info",
            "FortiCare License": "license_info",
            # Firmware
            "Firmware": "firmware_version",
            "FortiOS Version": "firmware_version",
            # VPN
            "VPN Tunnel": "vpn_tunnels",
            "IPSec VPN": "vpn_tunnels",
            "IPSec VPN Tunnels": "vpn_tunnels",
            # Routing
            "Routing Table": "routing_table",
            "Static Route": "routing_table",
            "Static Routes": "routing_table",
            "Static Route & Routing Table": "routing_table",
            # Uptime
            "System Uptime": "system_uptime",
            # GUI & CLI
            "GUI Access": "gui_access",
            "CLI Access": "cli_access",
            "SSH Access": "cli_access",
            "Accessed via CLI": "cli_access",
            "Firewall Internet Access": "cli_access",
            # Signatures
            "Signature Version": "signature_version",
            "Definitions": "signature_version",
            # Datetime
            "System Date and Time": "firewall_datetime",
            "Firewall Date and Time": "firewall_datetime",
            # HA
            "High Availability": "ha_status",
            "High Availability Status": "ha_status",
            # System Event
            "Event Logs": "system_event",
            "System Events": "system_event",
            # Log Manager
            "Log Settings": "log_manager",
            "Logging Settings": "log_manager",
            # Backup
            "Configuration Backup": "backup_configuration",
            "Backup Config": "backup_configuration",
        }
        for caption, expected_cat in variants.items():
            with self.subTest(caption=caption):
                self.assertEqual(normalize_appendix_caption(caption), expected_cat)

    def test_case_whitespace_and_punctuation(self):
        """Punctuation, case, and numbering prefixes are handled gracefully."""
        cases = [
            ("appendix 1: memory usage", "memory_usage"),
            ("APPENDIX 02 - CPU UTILIZATION", "cpu_usage"),
            ("  Appendix 07 -- Static Routes & Routing Table   ", "routing_table"),
            ("Appendix 10: Accessed via CLI / SSH", "cli_access"),
            ("Appendix 12: Firewall Date & Time.", "firewall_datetime"),
            ("ha-status", "ha_status"),
        ]
        for caption, expected in cases:
            with self.subTest(caption=caption):
                self.assertEqual(normalize_appendix_caption(caption), expected)

    def test_unrecognized_and_ambiguous_captions(self):
        """Unrecognized or ambiguous captions return None / unresolved without guessing."""
        unrecognized = [
            "Miscellaneous Appendix Information",
            "Hardware Serial Label Photo",
            "Customer Network Architecture Diagram",
            "Random Vendor Appendix XYZ",
            "",
            None,
        ]
        for caption in unrecognized:
            with self.subTest(caption=caption):
                self.assertIsNone(normalize_appendix_caption(caption))
                res = resolve_appendix_ground_truth(1, caption, is_verified_canonical=False)
                self.assertEqual(res["semantic_category"], "unresolved")
                self.assertIsNone(res["canonical_target_appendix"])
                self.assertEqual(res["ground_truth_source"], GroundTruthSource.UNRESOLVED.value)

    def test_verified_canonical_template_fallback(self):
        """When template is verified canonical, missing/unresolved captions fall back to canonical slot map."""
        res = resolve_appendix_ground_truth(1, "Unclear Section Header", is_verified_canonical=True)
        self.assertEqual(res["semantic_category"], "cpu_usage")
        self.assertEqual(res["canonical_target_appendix"], 1)
        self.assertEqual(res["ground_truth_source"], GroundTruthSource.VERIFIED_CANONICAL_TEMPLATE.value)
        self.assertTrue(res["is_source_slot_canonical"])

class TestNoncanonicalReportOrder(unittest.TestCase):
    """
    Step 28 Requirement:
    Verify synthetic non-canonical manifest fixture:
    Appendix 1 caption = Memory Usage
    Appendix 2 caption = CPU Usage
    Appendix 13 caption = CLI Access
    Appendix 14 caption = HA Status
    """
    def test_noncanonical_synthetic_fixture_mapping(self):
        fixture = [
            (1, "Memory Usage", "memory_usage", 2, False),
            (2, "CPU Usage", "cpu_usage", 1, False),
            (13, "CLI Access", "cli_access", 10, False),
            (14, "HA Status", "ha_status", 13, False),
        ]
        for src_app, caption, expected_sem, expected_tgt, expected_canon in fixture:
            with self.subTest(src_app=src_app):
                res = resolve_appendix_ground_truth(src_app, caption, is_verified_canonical=False)
                self.assertEqual(res["source_appendix_number"], src_app)
                self.assertEqual(res["semantic_category"], expected_sem)
                self.assertEqual(res["canonical_target_appendix"], expected_tgt)
                self.assertEqual(res["is_source_slot_canonical"], expected_canon)
                self.assertEqual(res["ground_truth_source"], GroundTruthSource.CAPTION.value)

    def test_classifier_evaluator_evaluates_semantic_correctness_in_noncanonical_slot(self):
        """
        Verify that when screenshot in Appendix 1 contains Memory Usage content,
        the evaluator correctly marks it as correct because its semantic category matches,
        instead of wrongly checking against canonical slot 1 (cpu_usage).
        """
        # Memory screenshot
        mem_text = "FortiGate Memory Utilization 45% Active 3200MB Total 8192MB"
        sc = make_dummy_screenshot(mem_text, "app_01_memory.png")

        # Evaluate screenshot appearing in historical Appendix 1 with caption 'Memory Usage'
        eval_res = classifier_evaluator.evaluate_screenshot(
            case_id="synthetic_case_noncanonical",
            appendix_number=1,
            image_index=1,
            image_filename="app_01_memory.png",
            screenshot=sc,
            source_caption="Memory Usage",
            is_verified_canonical=False,
        )

        self.assertEqual(eval_res["source_appendix_number"], 1)
        self.assertEqual(eval_res["expected_category"], "memory_usage")
        self.assertEqual(eval_res["canonical_target_appendix"], 2)
        self.assertFalse(eval_res["is_source_slot_canonical"])
        self.assertEqual(eval_res["predicted_category"], "memory_usage")
        # Evaluator marks it correct!
        self.assertTrue(eval_res["correct"])

if __name__ == "__main__":
    unittest.main()
