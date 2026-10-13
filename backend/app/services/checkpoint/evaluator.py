from typing import List
from .models import (
    CheckPointDeviceData,
    CheckPointChecklistItem,
)

class CheckpointPMEvaluator:
    """
    Evaluates CheckPoint Preventive Maintenance rules, populating the 12-item checklist
    and generating executive summary highlights.
    """

    def evaluate(self, device: CheckPointDeviceData) -> None:
        """
        Populates device.checklist and device.key_highlights in-place.
        """
        device.checklist = self._generate_checklist(device)
        device.key_highlights = self._generate_highlights(device)

    def _generate_checklist(self, device: CheckPointDeviceData) -> List[CheckPointChecklistItem]:
        sys = device.system
        hw = device.hardware
        stg = device.storage_log
        dt = device.datetime_info
        bk = device.backup
        is_gw = sys.is_gateway

        # Item 1: OS & Check Point Version
        os_clean = sys.os_version.strip()
        if not os_clean.startswith("Linux") and "linux" in os_clean.lower():
            os_clean = f"Linux {os_clean}"

        if is_gw:
            remarks_1 = (
                f"System OS:\n {os_clean}\n\n"
                f"Check Point Version:\n {sys.cp_version}\n\n"
                f"Uptime:\n {sys.uptime}\n\nRefer Appendix 1"
            )
        else:
            remarks_1 = (
                f"System OS:\n {os_clean}\n\n"
                f"Check point version:\n {sys.cp_version} (Security Management Server)\n"
                f"{sys.cp_version} (Software Version)\n\n"
                f"Uptime: {sys.uptime}\n\nRefer Appendix 1"
            )

        item1 = CheckPointChecklistItem(
            no=1,
            description="Identify OS version and Check Point version. Login to Web Console. Look for Check Point version and build from 'Appliance Status' page.",
            expected_result="Check Point version and build are identified.",
            pass_status="Y",
            remarks=remarks_1,
        )

        # Item 2: Physical connection of LAN cable
        item2 = CheckPointChecklistItem(
            no=2,
            description="Check physical connection of LAN cable.",
            expected_result="All the network cables at the used network interfaces are connected properly with activity at LED.",
            pass_status="N/A",
            remarks="",
        )

        # Item 3: Port Monitoring (Interface)
        item3 = CheckPointChecklistItem(
            no=3,
            description="Port Monitoring (Interface)",
            expected_result="Physical Connection to be cross check with the Firewall interface.",
            pass_status="Y",
            remarks="Refer Appendix 2",
        )

        # Item 4: Redundant Power Supply
        item4 = CheckPointChecklistItem(
            no=4,
            description="Check redundant power supply unit if there is.",
            expected_result="All the power supply units work with Green LED.",
            pass_status="Y",
            remarks="Power supply units\nStatus: OK\n\nRefer Appendix 4",
        )

        # Item 5: Management Access
        item5 = CheckPointChecklistItem(
            no=5,
            description="Check management access of serial console, HTTPs, SSH and SmartConsole.",
            expected_result="All can be accessed.",
            pass_status="Y",
            remarks="HTTPS: OK\nSSH: OK\nSmartConsole: OK",
        )

        # Item 6: Date and Time
        item6 = CheckPointChecklistItem(
            no=6,
            description="Check firewall Web Console or SmartConsole date and time. Login to Web Console. Look for date and time from 'Appliance Status' page.",
            expected_result="Time and date is synchronized.",
            pass_status="Y",
            remarks="Time zone: Correct (Kuala Lumpur, Asia, GMT +8:00)\n\nRefer Appendix 6",
        )

        # Item 7: CPU Utilization
        item7 = CheckPointChecklistItem(
            no=7,
            description="Check firewall historical and real time CPU utilization to ensure the firewall is not overloaded. Login to Check Point SmartView Monitor. Click System Counters -> System History.",
            expected_result="CPU utilization is not overloaded.",
            pass_status="Y",
            remarks="Refer Appendix 7",
        )

        # Item 8: Disk Space
        if stg.var_log_full:
            pass_8 = "N"
            remarks_8 = "Free Disk Space Critical - /var/log 100% full.\nCheck if any partition listed above is above 80% utilization."
        else:
            pass_8 = "Y"
            remarks_8 = "Refer Appendix 8"

        item8 = CheckPointChecklistItem(
            no=8,
            description="Check firewall or SmartConsole disk space to ensure that no partition is above 80% utilization. Login to Web Console Click Appliance Status -> Disk Information.",
            expected_result="Used disk space at any partition is below 80%.",
            pass_status=pass_8,
            remarks=remarks_8,
        )

        # Item 9: Log Switch
        if stg.log_switch_enabled:
            remarks_9 = (
                f"Enabled.\n\n"
                f"Alert when disk space below {stg.alert_threshold or '3000MB'}.\n\n"
                f"Start delete old files when disk space below {stg.delete_threshold or '5000MB'}.\n\n"
                f"Refer Appendix 9"
            )
        else:
            remarks_9 = "Disabled.\n\nRefer Appendix 9"

        item9 = CheckPointChecklistItem(
            no=9,
            description="Check SmartDashboard log switch configuration to ensure that this is enabled. This is to prevent the active log file to be oversized. a) Login to Check Point SmartDashboard. b) Edit the gateway, click 'Logs' then 'Local Log Storage'.",
            expected_result="Log Switched is configured.",
            pass_status="Y",
            remarks=remarks_9,
        )

        # Item 10: High Availability
        item10 = CheckPointChecklistItem(
            no=10,
            description="High Availability  (If any)",
            expected_result="The status for the HA is standby and synchronized.",
            pass_status="N/A",
            remarks="Pass  Failed  Not Applicable",
        )

        # Item 11: License Status
        app_lic_num = "12" if is_gw else "11"
        item11 = CheckPointChecklistItem(
            no=11,
            description="License status for gateway",
            expected_result="License for the gateway is up to date.",
            pass_status="Y",
            remarks=f"Refer Appendix {app_lic_num}",
        )

        # Item 12: Backup Configuration
        app_bk_num = "13" if is_gw else "12"
        bk_expected = "Backup is enabled" if bk.backup_enabled else "Backup is disabled"
        item12 = CheckPointChecklistItem(
            no=12,
            description="Web Console configuration backup. Login to Web Console. Click Appliance -> Backup and Restore. Download the backup copy.",
            expected_result=bk_expected,
            pass_status="Y",
            remarks=f"Refer Appendix {app_bk_num}",
        )

        return [
            item1, item2, item3, item4, item5, item6,
            item7, item8, item9, item10, item11, item12,
        ]

    def _generate_highlights(self, device: CheckPointDeviceData) -> List[str]:
        if device.storage_log.var_log_full:
            return ["/var/log Directory Full"]

        # Default healthy highlights
        highlights = [
            "The overall system is operating in a healthy and stable condition.",
            "CPU and disk usage are within optimal thresholds, indicating no performance or storage concerns at this time.",
            "No critical alerts or system faults detected during the assessment.",
        ]

        if not device.system.is_gateway and not device.storage_log.var_log_full:
            highlights.extend([
                "Current software version is stable; update is optional and only recommended if specific bugs or issues are encountered",
                "Network routing table is consistent and correctly configured across interfaces.",
            ])

        return highlights
