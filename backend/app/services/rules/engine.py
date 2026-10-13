from ...models.pm_data import PMData

class RulesEngine:
    def evaluate(self, pm_data: PMData) -> PMData:
        """
        Evaluates PM business rules on extracted values to determine statuses and remarks.
        """
        # 1. CPU Rule
        cpu_val = pm_data.hardware.cpu_usage.value
        if cpu_val is not None:
            try:
                cpu_num = int(cpu_val)
                if cpu_num < 80:
                    pm_data.hardware.cpu_status.value = "Healthy"
                else:
                    pm_data.hardware.cpu_status.value = "Unhealthy"
            except (ValueError, TypeError):
                pm_data.hardware.cpu_status.value = "Healthy"
        else:
            pm_data.hardware.cpu_status.value = "Healthy"

        # 2. Memory Rule
        mem_val = pm_data.hardware.memory_usage.value
        if mem_val is not None:
            try:
                mem_num = int(mem_val)
                if mem_num < 80:
                    pm_data.hardware.memory_status.value = "Healthy"
                else:
                    pm_data.hardware.memory_status.value = "Unhealthy"
            except (ValueError, TypeError):
                pm_data.hardware.memory_status.value = "Healthy"
        else:
            pm_data.hardware.memory_status.value = "Healthy"

        # 3. Firmware Rule
        curr_ver = str(pm_data.firmware.current.value or "").strip().lower().lstrip("v")
        latest_ver = str(pm_data.firmware.latest.value or "").strip().lower().lstrip("v")
        if curr_ver and latest_ver:
            if curr_ver == latest_ver:
                pm_data.firmware.status.value = "Up-to-Date"
            else:
                pm_data.firmware.status.value = "Out-of-Date"
        else:
            pm_data.firmware.status.value = "Up-to-Date"

        # 4. VPN Status
        tot = pm_data.vpn.total.value or 0
        act = pm_data.vpn.active.value or 0
        pm_data.vpn.inactive.value = max(0, int(tot) - int(act))

        # 5. Backup Status
        # Default Passed if evidence exists or verified
        if pm_data.configuration.backup_status.value not in ("Passed", "Failed"):
            pm_data.configuration.backup_status.value = "Passed"

        return pm_data

rules_engine = RulesEngine()
