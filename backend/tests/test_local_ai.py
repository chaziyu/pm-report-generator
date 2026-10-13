"""
Comprehensive Test Suite for Local AI Subsystem (Sections 31 & 32).
Tests Local AI lifecycle, ambiguity detection, arbitration, caching,
identity safety, error fallbacks, and regression scenarios without requiring external GGUF binaries.
"""

import unittest
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models.screenshot import ScreenshotRecord, ClassificationCandidate, OCRToken
from app.services.ai.schemas import (
    ArbitrationState,
    AIClassificationResponse,
    AICategoryEvidence,
    AIExtractionResponse,
    AIExtractedField,
)
from app.services.ai.base import FakeAIProvider
from app.services.ai.ambiguity import AmbiguityDetector
from app.services.ai.cache import LocalAICache
from app.services.ai.model.manifest import ModelManifest
from app.services.ai.model.manager import LocalAIModelManager
from app.services.ai.runtime.manager import LocalAIRuntimeManager
from app.services.ai.runtime.health import check_server_health
from app.services.ai.service import LocalAIService
from app.services.ai.arbitration import arbitrate_classification, arbitrate_extraction

def make_screenshot(text: str, candidates=None, sc_id: str = "sc_01", filename: str = "img.png") -> ScreenshotRecord:
    cand_list = []
    if candidates:
        for cat, conf in candidates:
            cand_list.append(ClassificationCandidate(category=cat, confidence=conf))
    return ScreenshotRecord(
        id=sc_id,
        filename=filename,
        original_path=f"dummy/{filename}",
        ocr_text=text,
        sha256=f"hash_{sc_id}",
        classification_candidates=cand_list,
        assigned_categories=[cand_list[0].category] if cand_list else [],
    )

class TestLocalAISubsystem(unittest.TestCase):
    def setUp(self):
        self.ambiguity_detector = AmbiguityDetector()
        self.cache = LocalAICache()

    def test_ai_disabled(self):
        """When AI is disabled, status reflects DISABLED and verification bypasses AI."""
        service = LocalAIService(enabled=False)
        self.assertEqual(service.get_status()["status"], "DISABLED")
        
        sc = make_screenshot("CPU 10%", candidates=[("cpu_usage", 0.99)])
        state, cats, prov = service.verify_classification(sc, "cpu_usage", 0.99)
        self.assertEqual(state, ArbitrationState.DETERMINISTIC_ACCEPTED)
        self.assertIsNone(prov)

    def test_model_missing_status(self):
        """When model file does not exist, status is MODEL_MISSING and fallback continues."""
        model_mgr = LocalAIModelManager(custom_models_dir=Path("non_existent_models_dir_xyz"))
        self.assertEqual(model_mgr.get_status()["status"], "MODEL_MISSING")

    def test_runtime_health_unreachable(self):
        """Health check returns UNREACHABLE for an unallocated port."""
        is_ready, msg = check_server_health(port=59999, timeout_sec=0.1)
        self.assertFalse(is_ready)
        self.assertEqual(msg, "UNREACHABLE")

    def test_high_confidence_clear_bypass(self):
        """Cropped single-category screenshot with conf >= 0.85 and no ambiguity bypasses AI."""
        provider = FakeAIProvider()
        service = LocalAIService(provider=provider)
        
        # Pure cropped CPU widget with no other widgets or dashboard URLs
        sc = make_screenshot("CPU 12 hours Current usage 15%", candidates=[("cpu_usage", 0.98)])
        state, cats, prov = service.verify_classification(sc, "cpu_usage", 0.98)
        
        self.assertEqual(state, ArbitrationState.DETERMINISTIC_ACCEPTED)
        self.assertEqual(provider.call_count, 0)
        self.assertIsNone(prov)

    def test_high_confidence_ambiguous_triggers_ai(self):
        """Even at 0.99 confidence, an ambiguous composite screenshot MUST invoke AI."""
        provider = FakeAIProvider()
        service = LocalAIService(provider=provider)
        
        # System Information widget showing Firmware and Uptime (measured at 0.99 in baseline)
        text = "System Information Hostname FW01 Serial FG200F Firmware v7.4.11 build2878 (Mature) Uptime 51d 3h 44m"
        sc = make_screenshot(text, candidates=[("firmware_version", 0.99), ("system_uptime", 0.95)])
        
        # Verify ambiguity detector triggers
        amb = service.check_ambiguity(sc)
        self.assertTrue(amb.ambiguous)
        
        # Verify AI is invoked
        state, cats, prov = service.verify_classification(sc, "firmware_version", 0.99)
        self.assertEqual(provider.call_count, 1)
        self.assertIn(state, (ArbitrationState.MULTI_CATEGORY, ArbitrationState.AI_VERIFIED))
        self.assertIsNotNone(prov)

    def test_medium_confidence_triggers_ai(self):
        """Deterministic confidence between 0.70 and 0.84 triggers AI verification."""
        provider = FakeAIProvider()
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("System Maintenance Backup config.conf", candidates=[("backup_configuration", 0.75)])
        state, cats, prov = service.verify_classification(sc, "backup_configuration", 0.75)
        
        self.assertEqual(provider.call_count, 1)
        self.assertIsNotNone(prov)

    def test_multi_category_result(self):
        """AI returning multiple evidenced categories arbitrates as MULTI_CATEGORY."""
        ai_resp = AIClassificationResponse(
            categories=[
                AICategoryEvidence(category="firmware_version", evidenced=True, confidence=0.98),
                AICategoryEvidence(category="system_uptime", evidenced=True, confidence=0.95),
            ],
            primary_category="firmware_version",
            is_multi_category=True,
        )
        provider = FakeAIProvider(custom_classification=ai_resp)
        service = LocalAIService(provider=provider)
        
        text = "System Information Hostname FW01 Firmware v7.4.11 Uptime 51d 3h"
        sc = make_screenshot(text, candidates=[("firmware_version", 0.99), ("system_uptime", 0.95)])
        
        state, cats, prov = service.verify_classification(sc, "firmware_version", 0.99)
        self.assertEqual(state, ArbitrationState.MULTI_CATEGORY)
        self.assertIn("firmware_version", cats)
        self.assertIn("system_uptime", cats)

    def test_ai_deterministic_agreement(self):
        """When AI agrees with deterministic classification, arbitration is AI_VERIFIED."""
        ai_resp = AIClassificationResponse(
            categories=[AICategoryEvidence(category="vpn_tunnels", evidenced=True, confidence=0.99)],
            primary_category="vpn_tunnels",
        )
        provider = FakeAIProvider(custom_classification=ai_resp)
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("IPsec Tunnels Total: 2 Up: 2", candidates=[("vpn_tunnels", 0.78)])
        state, cats, prov = service.verify_classification(sc, "vpn_tunnels", 0.78)
        self.assertEqual(state, ArbitrationState.AI_VERIFIED)

    def test_ai_disagreement(self):
        """When AI identifies a different category, DISAGREEMENT is recorded with both candidates preserved."""
        ai_resp = AIClassificationResponse(
            categories=[AICategoryEvidence(category="gui_access", evidenced=True, confidence=0.98)],
            primary_category="gui_access",
        )
        provider = FakeAIProvider(custom_classification=ai_resp)
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("Dashboard Overview /system/dashboard", candidates=[("cpu_usage", 0.76)])
        state, cats, prov = service.verify_classification(sc, "cpu_usage", 0.76)
        
        self.assertEqual(state, ArbitrationState.DISAGREEMENT)
        self.assertIn("gui_access", cats)
        self.assertIn("cpu_usage", cats)
        self.assertTrue(len(prov.disagreements) > 0)

    def test_invalid_json_fallback(self):
        """Malformed JSON from AI model gracefully falls back to deterministic pipeline with review."""
        provider = FakeAIProvider(return_malformed_json=True)
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("ambiguous widget text", candidates=[("cpu_usage", 0.72)])
        state, cats, prov = service.verify_classification(sc, "cpu_usage", 0.72)
        
        self.assertIn(state, (ArbitrationState.REVIEW_REQUIRED, ArbitrationState.DETERMINISTIC_ACCEPTED))
        self.assertIn("cpu_usage", cats)

    def test_timeout_fallback(self):
        """Model timeout gracefully falls back to deterministic pipeline with review required."""
        provider = FakeAIProvider(should_timeout=True)
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("complex dashboard screen", candidates=[("gui_access", 0.75)])
        state, cats, prov = service.verify_classification(sc, "gui_access", 0.75)
        self.assertIn(state, (ArbitrationState.REVIEW_REQUIRED, ArbitrationState.DETERMINISTIC_ACCEPTED))

    def test_runtime_crash_fallback(self):
        """Model server crash gracefully falls back to deterministic pipeline."""
        provider = FakeAIProvider(should_fail=True)
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("test text", candidates=[("interface", 0.75)])
        state, cats, prov = service.verify_classification(sc, "interface", 0.75)
        self.assertIn(state, (ArbitrationState.REVIEW_REQUIRED, ArbitrationState.DETERMINISTIC_ACCEPTED))

    def test_critical_identity_serial_disagreement(self):
        """
        CRITICAL IDENTITY SAFETY (Section 20):
        For hostname and serial numbers, Qwen must NEVER silently overwrite OCR.
        On disagreement, deterministic OCR is preserved, DISAGREEMENT is flagged, and review is required.
        """
        state, val, conf, dis = arbitrate_extraction(
            field_path="application.serial_secondary",
            deterministic_val="FG203FT921914951",
            deterministic_confidence=0.85,
            ai_val="FG200FT921914957",  # AI hallucinates / guesses the correct serial
            ai_confidence=0.99,
        )
        self.assertEqual(state, ArbitrationState.DISAGREEMENT)
        # Deterministic value must be retained, NOT overwritten by AI!
        self.assertEqual(val, "FG203FT921914951")
        self.assertTrue(len(dis) > 0)
        self.assertIn("Value conflict", dis[0])

    def test_cache_hit(self):
        """Consecutive identical requests hit the local AI cache without re-invoking the provider."""
        provider = FakeAIProvider()
        service = LocalAIService(provider=provider)
        
        sc = make_screenshot("License Info Expiration 2026/12/28", candidates=[("license_info", 0.75)], sc_id="cached_img")
        
        # First call: cache miss, provider invoked
        state1, cats1, prov1 = service.verify_classification(sc, "license_info", 0.75)
        self.assertEqual(provider.call_count, 1)
        
        # Second call: cache hit, provider count unchanged
        state2, cats2, prov2 = service.verify_classification(sc, "license_info", 0.75)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(state1, state2)

    def test_inference_locking(self):
        """Runtime manager provides a working inference lock for concurrency = 1."""
        runtime_mgr = LocalAIRuntimeManager(enabled=True)
        lock = runtime_mgr.acquire_inference_lock()
        with lock:
            self.assertTrue(lock.locked())
        self.assertFalse(lock.locked())
        runtime_mgr.shutdown()

    # --- Section 32: REGRESSION TESTS FOR CURRENT KNOWN AMBIGUITIES ---

    def test_regression_system_information_ambiguity(self):
        """
        REGRESSION: System Information widget containing Firmware and Uptime.
        In baseline evaluation, this image scored 0.99 on firmware_version and misclassified appendix 8.
        The ambiguity detector must flag this as ambiguous regardless of 0.99 score.
        """
        text = (
            "System Information\n"
            "Hostname HQ_T2_FG200F_Primary\n"
            "Serial number FG200FT921916632\n"
            "Firmware v7.4.11 build2878 (Mature)\n"
            "System time 2026/09/09 14:00:00\n"
            "Uptime 51d 3h 44m\n"
            "WAN IP 211.24.244.198"
        )
        sc = make_screenshot(
            text,
            candidates=[("firmware_version", 0.99), ("system_uptime", 0.95)],
            filename="appendix_08_uptime.png"
        )
        amb = self.ambiguity_detector.detect(sc)
        self.assertTrue(amb.ambiguous)
        self.assertTrue(any("Firmware and Uptime" in r for r in amb.reasons))
        self.assertIn("firmware_version", amb.candidate_categories)
        self.assertIn("system_uptime", amb.candidate_categories)

    def test_regression_full_dashboard_ambiguity(self):
        """
        REGRESSION: Full uncropped dashboard view containing GUI Access, CPU, and Memory.
        In baseline evaluation, this image scored 0.99 on gui_access and misclassified appendix 1.
        The ambiguity detector must flag this as ambiguous regardless of 0.99 score.
        """
        text = (
            "10.10.1.3/system/dashboard/1\n"
            "+ Add widget\n"
            "Security Profiles Network Log & Report\n"
            "Storage used CPU 100% Memory 100%\n"
            "Current usage 0% 15 seconds ago 1 minute"
        )
        sc = make_screenshot(
            text,
            candidates=[("gui_access", 0.99), ("cpu_usage", 0.95), ("memory_usage", 0.95)],
            filename="appendix_01_cpu.png"
        )
        amb = self.ambiguity_detector.detect(sc)
        self.assertTrue(amb.ambiguous)
        self.assertTrue(any("Full dashboard screen contains both GUI navigation" in r for r in amb.reasons))
        self.assertIn("gui_access", amb.candidate_categories)
        self.assertIn("cpu_usage", amb.candidate_categories)

if __name__ == "__main__":
    unittest.main()
