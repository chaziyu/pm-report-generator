"""
Sanitized Regression Tests for Pipeline Evaluation and Hardening.
Tests specific fixes discovered during dataset evaluation:
- Classification profile precision and tie-breaking
- Regex parsing hardening (firmware IP collision, uptime formats, VPN tunnel syntax, license expiry dates)
- Hostname label suppression and device header fallback
- Cross-widget isolation (CPU vs Memory widgets on dashboard)
All tests use synthetic text/tokens to avoid exposing customer data.
"""

import unittest
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.classification.classifier import ScreenshotClassifier
from app.services.extraction.system_info import SystemInfoExtractor
from app.services.extraction.resources import ResourceExtractor
from app.services.extraction.vpn import VpnExtractor
from app.services.extraction.licensing import LicensingExtractor
from app.services.extraction.extractor import MasterExtractor
from app.models.screenshot import ScreenshotRecord, OCRToken
from app.models.pm_data import PMData

def make_screenshot(text: str, image_id: str = "img_test") -> ScreenshotRecord:
    """Helper to create a ScreenshotRecord with plain text and tokens."""
    tokens = []
    for word in text.strip().split():
        tokens.append(OCRToken(text=word, bbox=[0, 0, 10, 10], confidence=0.99))
    return ScreenshotRecord(
        id=image_id,
        filename=f"{image_id}.png",
        original_path=f"dummy/{image_id}.png",
        ocr_text=text,
        ocr_tokens=tokens
    )


class TestClassificationHardening(unittest.TestCase):
    def setUp(self):
        self.classifier = ScreenshotClassifier()

    def test_gui_access_vs_dashboard_widget(self):
        """Dashboard widgets should not be classified as gui_access just because FortiGate is present."""
        cpu_text = "FortiGate 200F\nCPU\nCurrent usage 14%\nCore 1 Core 2"
        rec_cpu = make_screenshot(cpu_text, "cpu")
        self.classifier.classify(rec_cpu)
        self.assertIn("cpu_usage", rec_cpu.assigned_categories)
        self.assertNotIn("gui_access", rec_cpu.assigned_categories)

        # True GUI access dashboard view has /system/dashboard or + add widget
        gui_text = "FortiGate /system/dashboard/status\n+ Add Widget\nAdministrator superadmin\nDashboard"
        rec_gui = make_screenshot(gui_text, "gui")
        self.classifier.classify(rec_gui)
        self.assertIn("gui_access", rec_gui.assigned_categories)

    def test_routing_table_vs_interface(self):
        """Interface screens containing sidebar navigation with 'Routing' should not be classified as routing_table."""
        interface_text = "FortiGate /ng/interface Network Interfaces\nport1 Physical WAN connected 1000Mbps\nport2 LAN connected\nRouting\nSystem"
        rec_if = make_screenshot(interface_text, "if")
        self.classifier.classify(rec_if)
        self.assertIn("interface", rec_if.assigned_categories)
        self.assertNotIn("routing_table", rec_if.assigned_categories)

        # Routing table CLI or GUI
        routing_text = "Codes: K - kernel, C - connected, S - static, R - RIP\nS 0.0.0.0/0 [10/0] via 192.168.1.1, port1\nC 192.168.1.0/24 is directly connected, port1"
        rec_rt = make_screenshot(routing_text, "rt")
        self.classifier.classify(rec_rt)
        self.assertIn("routing_table", rec_rt.assigned_categories)

    def test_cli_access_prompt(self):
        """CLI screens with prompt $ or # and commands/ping statistics should be classified as cli_access."""
        cli_text = "LAB-FW01 # get system status\nVersion: FortiGate-200F\nLAB-FW01 # execute ping 8.8.8.8\n--- 8.8.8.8 ping statistics ---"
        rec_cli = make_screenshot(cli_text, "cli")
        self.classifier.classify(rec_cli)
        self.assertIn("cli_access", rec_cli.assigned_categories)

    def test_backup_configuration_tokens(self):
        """Backup configuration screens with file downloads and .conf extensions."""
        backup_text = "System Maintenance Backup\nDownload file: backup_config_2026_09_26.conf\nSize: 450 KB done"
        rec_bk = make_screenshot(backup_text, "bk")
        self.classifier.classify(rec_bk)
        self.assertIn("backup_configuration", rec_bk.assigned_categories)

    def test_system_uptime_compact_regex_matching(self):
        """Compact elapsed uptime like 51d3h44m or 177d14h24m9s should be supported in system_uptime."""
        uptime_text = "System Information\nHostname: FW01\nUptime: 51d3h44m\nCurrent time: 2026/09/09"
        rec_ut = make_screenshot(uptime_text, "ut")
        self.classifier.classify(rec_ut)
        self.assertIn("system_uptime", rec_ut.assigned_categories)

    def test_gui_access_dashboard_overview(self):
        """Full dashboard overview captures with administrator, system, and licenses should classify as gui_access."""
        gui_text = "FortiGate 10.10.1.3/system/dashboard/1\n+ Add Widget\nAdministrator superadmin\nLicenses Security Fabric Sessions"
        rec_gui = make_screenshot(gui_text, "gui_ov")
        self.classifier.classify(rec_gui)
        self.assertIn("gui_access", rec_gui.assigned_categories)
        self.assertEqual(rec_gui.classification_candidates[0].category, "gui_access")



class TestSystemInfoExtractionHardening(unittest.TestCase):
    def setUp(self):
        self.extractor = SystemInfoExtractor()

    def test_hostname_ignores_labels(self):
        """Hostname extractor should reject generic labels like 'Serial Number', 'Firmware', etc."""
        text = "Host name : Serial Number\nDevice : HQ_EDGE_FIREWALL_01"
        rec = make_screenshot(text)
        res = self.extractor.extract_hostname(rec)
        self.assertIsNotNone(res)
        self.assertEqual(res.value, "HQ_EDGE_FIREWALL_01")

    def test_firmware_no_ip_collision(self):
        """Firmware extractor should not mistake IP address segments (e.g. 10.7.4.1) for firmware versions."""
        text = "Interface IP: 10.7.4.1/24\nFirmware: v7.4.4,build2878 (Mature)\nNext Hop: 10.7.4.254"
        rec = make_screenshot(text)
        res = self.extractor.extract_firmware(rec)
        self.assertIsNotNone(res["version"])
        self.assertEqual(res["version"].value, "7.4.4")
        self.assertIsNotNone(res["build"])
        self.assertEqual(res["build"].value, "2878")
        self.assertIsNotNone(res["maturity"])
        self.assertEqual(res["maturity"].value, "Mature")

    def test_firmware_maturity_requires_parentheses(self):
        """Maturity should not match random occurrences of 'Feature' in 'Feature Visibility'."""
        text = "System Menu: Feature Visibility\nVersion: 7.2.5 (Feature)"
        rec = make_screenshot(text)
        res = self.extractor.extract_firmware(rec)
        self.assertIsNotNone(res["maturity"])
        self.assertEqual(res["maturity"].value, "Feature")

    def test_uptime_formats(self):
        """Uptime extractor should support compact, colon-separated, and verbose formats."""
        # Verbose
        t1 = make_screenshot("System Uptime: 177 days 14 hours 24 minutes")
        res1 = self.extractor.extract_uptime(t1)
        self.assertIsNotNone(res1)
        self.assertEqual(res1.value, "177 days 14 hours 24 minutes")

        # Compact d h m
        t2 = make_screenshot("Uptime: 51d 3h44m")
        res2 = self.extractor.extract_uptime(t2)
        self.assertIsNotNone(res2)
        self.assertEqual(res2.value, "51 day(s) 3 hour(s) 44 min(s)")

        # Colon compact
        t3 = make_screenshot("System Uptime: 20:04:12 (day:hour:min)")
        res3 = self.extractor.extract_uptime(t3)
        self.assertIsNotNone(res3)
        self.assertEqual(res3.value, "20:04:12 (day:hour:min)")


class TestResourceExtractionHardening(unittest.TestCase):
    def setUp(self):
        self.extractor = ResourceExtractor()

    def test_cpu_memory_cross_isolation(self):
        """CPU and Memory extractors must not confuse values when both labels appear on a screen."""
        text = "CPU\nCurrent usage 18%\nMemory\nCurrent usage 62%"
        rec = make_screenshot(text)
        cpu = self.extractor.extract_cpu(rec)
        mem = self.extractor.extract_memory(rec)
        self.assertIsNotNone(cpu)
        self.assertEqual(cpu.value, 18)
        self.assertIsNotNone(mem)
        self.assertEqual(mem.value, 62)


class TestVpnAndLicensingExtractionHardening(unittest.TestCase):
    def test_vpn_tunnel_syntax(self):
        extractor = VpnExtractor()
        # FortiOS dashboard format: Tunnels Total: 2 Static/DDNS: 2 Up 2 Down 0
        text = "IPsec Tunnels Total: 2 Static/DDNS: 2 Up 2 Down 0 Dialup: 0"
        rec = make_screenshot(text)
        res = extractor.extract_vpn_stats(rec)
        self.assertEqual(res["total"].value, 2)
        self.assertEqual(res["active"].value, 2)
        self.assertEqual(res["inactive"].value, 0)

    def test_licensing_expiration_conversion(self):
        extractor = LicensingExtractor()
        # FortiOS license format: Licensed (Expiration Date: 2026/12/28)
        text = "FortiCare Support: Licensed (Expiration Date: 2026/12/28)\nAntivirus: Licensed"
        rec = make_screenshot(text)
        res = extractor.extract_license_info(rec)
        self.assertIsNotNone(res["expiry_date"])
        self.assertEqual(res["expiry_date"].value, "28/12/2026")


class TestMasterExtractorIntegration(unittest.TestCase):
    def setUp(self):
        self.master = MasterExtractor()

    def test_uptime_precedence(self):
        """Dedicated system_uptime appendix should override generic timestamp in appendix 5."""
        res_app5 = make_screenshot("System Information\nUptime: 01:23:45 (day:hour:min)", "app5")
        res_app5.assigned_categories = ["firmware_version"]
        res_app8 = make_screenshot("System Uptime\n177 days 14 hours 24 minutes", "app8")
        res_app8.assigned_categories = ["system_uptime"]

        pm_data = PMData()
        self.master.extract_all([res_app5, res_app8], pm_data)
        self.assertEqual(pm_data.configuration.uptime.value, "177 days 14 hours 24 minutes")

    def test_license_date_precedence(self):
        """Explicit license expiration date should not be overwritten by report timestamp."""
        res_app4 = make_screenshot("FortiCare Licensed (Expiration Date: 2028/04/12)", "app4")
        res_app4.assigned_categories = ["license_info"]
        res_app12 = make_screenshot("System Time: 2026/09/09 14:00:00", "app12")
        res_app12.assigned_categories = ["firewall_datetime"]

        pm_data = PMData()
        self.master.extract_all([res_app4, res_app12], pm_data)
        self.assertEqual(pm_data.licensing.expiry_date.value, "12/04/2028")


if __name__ == "__main__":
    unittest.main()
