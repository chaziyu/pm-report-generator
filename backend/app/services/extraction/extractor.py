from typing import List
from ...models.screenshot import ScreenshotRecord
from ...models.pm_data import PMData
from .resources import resource_extractor
from .system_info import system_info_extractor
from .vpn import vpn_extractor
from .licensing import licensing_extractor

class MasterExtractor:
    def extract_all(self, screenshots: List[ScreenshotRecord], pm_data: PMData) -> PMData:
        """
        Coordinates all specific extractors across classified screenshots.
        Updates PMData fields only with higher-confidence extractions.
        """
        for sc in screenshots:
            cats = sc.assigned_categories

            # Resource Extraction (CPU / Memory)
            # Guard: Dedicated memory screenshots should not trigger CPU extraction and vice-versa
            if ("cpu_usage" in cats or "cpu" in sc.ocr_text.lower()) and "memory_usage" not in cats:
                cpu_val = resource_extractor.extract_cpu(sc)
                if cpu_val and (pm_data.hardware.cpu_usage.value is None or cpu_val.confidence >= pm_data.hardware.cpu_usage.confidence):
                    pm_data.hardware.cpu_usage = cpu_val

            if ("memory_usage" in cats or "memory" in sc.ocr_text.lower()) and "cpu_usage" not in cats:
                mem_val = resource_extractor.extract_memory(sc)
                if mem_val and (pm_data.hardware.memory_usage.value is None or mem_val.confidence >= pm_data.hardware.memory_usage.confidence):
                    pm_data.hardware.memory_usage = mem_val

            # System Information Extraction
            if any(c in cats for c in ("firmware_version", "system_uptime", "gui_access")) or "hostname" in sc.ocr_text.lower() or "serial" in sc.ocr_text.lower():
                # Hostname
                hn = system_info_extractor.extract_hostname(sc)
                if hn and (not pm_data.application.hostname.value or hn.confidence > pm_data.application.hostname.confidence):
                    pm_data.application.hostname = hn

                # Serials
                pri, sec = system_info_extractor.extract_serials(sc)
                if pri and (not pm_data.application.serial_primary.value or pri.confidence > pm_data.application.serial_primary.confidence):
                    pm_data.application.serial_primary = pri
                if sec and (not pm_data.application.serial_secondary.value or sec.confidence > pm_data.application.serial_secondary.confidence):
                    pm_data.application.serial_secondary = sec

                # Firmware
                fw_data = system_info_extractor.extract_firmware(sc)
                if fw_data.get("version"):
                    pm_data.firmware.current = fw_data["version"]
                if fw_data.get("build"):
                    pm_data.firmware.build = fw_data["build"]
                if fw_data.get("maturity"):
                    pm_data.firmware.maturity = fw_data["maturity"]

                # Uptime - give dedicated system_uptime screenshots priority (confidence 0.99)
                upt = system_info_extractor.extract_uptime(sc)
                if upt:
                    if "system_uptime" in cats:
                        upt.confidence = 0.99
                    if not pm_data.configuration.uptime.value or upt.confidence >= pm_data.configuration.uptime.confidence:
                        pm_data.configuration.uptime = upt

                # Timezone
                tz = system_info_extractor.extract_timezone(sc)
                if tz and (not pm_data.configuration.timezone.value or tz.confidence > pm_data.configuration.timezone.confidence):
                    pm_data.configuration.timezone = tz

            # VPN Extraction: Only accept if classified as vpn_tunnels or non-zero tunnels detected
            if "vpn_tunnels" in cats or "ipsec stats tunnel" in sc.ocr_text.lower():
                vpn_data = vpn_extractor.extract_vpn_stats(sc)
                if vpn_data["total"].value is not None and (int(vpn_data["total"].value) > 0 or "vpn_tunnels" in cats):
                    if pm_data.vpn.total.value == 0 or int(vpn_data["total"].value) > 0:
                        pm_data.vpn.total = vpn_data["total"]
                        pm_data.vpn.active = vpn_data["active"]
                        pm_data.vpn.inactive = vpn_data["inactive"]

            # Licensing Extraction: Trigger on license_info or signature_version (which contains FortiGuard licenses)
            if any(c in cats for c in ("license_info", "signature_version")) or any(k in sc.ocr_text.lower() for k in ("forticare", "licensed", "expiration date")):
                lic_data = licensing_extractor.extract_license_info(sc)
                pm_data.licensing.forticare_status = lic_data["forticare_status"]
                if lic_data.get("expiry_date") and lic_data["expiry_date"].value:
                    if pm_data.licensing.expiry_date.value is None or lic_data["expiry_date"].confidence >= pm_data.licensing.expiry_date.confidence:
                        pm_data.licensing.expiry_date = lic_data["expiry_date"]
                pm_data.licensing.antivirus = lic_data["antivirus"]
                pm_data.licensing.ips = lic_data["ips"]
                pm_data.licensing.web_filter = lic_data["web_filter"]
                pm_data.licensing.anti_spam = lic_data["anti_spam"]

            # HA Status
            if "ha_status" in cats or "high availability" in sc.ocr_text.lower():
                pm_data.configuration.ha_status.value = "Pass"
                pm_data.configuration.ha_status.source_screenshot_id = sc.id

            # Backup
            if "backup_configuration" in cats or ".conf" in sc.ocr_text.lower():
                pm_data.configuration.backup_status.value = "Passed"
                pm_data.configuration.backup_status.source_screenshot_id = sc.id

        return pm_data

master_extractor = MasterExtractor()
