from typing import List
from ...models.session import Session
from ...models.validation import ValidationIssue

class ConsistencyValidator:
    def validate(self, session: Session) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        pm = session.pm_data

        # 1. CPU consistency check
        if pm.hardware.cpu_usage.value is not None:
            try:
                cpu = int(pm.hardware.cpu_usage.value)
                if cpu >= 80 and pm.hardware.cpu_status.value == "Healthy":
                    issues.append(ValidationIssue(
                        id="val_cpu_inconsistency",
                        severity="ERROR",
                        field="cpu_usage",
                        appendix_number=1,
                        message=f"CPU usage is {cpu}% (>= 80%) but status is marked Healthy.",
                        blocking=True
                    ))
            except (ValueError, TypeError):
                pass

        # 2. Memory consistency check
        if pm.hardware.memory_usage.value is not None:
            try:
                mem = int(pm.hardware.memory_usage.value)
                if mem >= 80 and pm.hardware.memory_status.value == "Healthy":
                    issues.append(ValidationIssue(
                        id="val_mem_inconsistency",
                        severity="ERROR",
                        field="memory_usage",
                        appendix_number=2,
                        message=f"Memory usage is {mem}% (>= 80%) but status is marked Healthy.",
                        blocking=True
                    ))
            except (ValueError, TypeError):
                pass

        # 3. VPN counts check
        try:
            tot = int(pm.vpn.total.value or 0)
            act = int(pm.vpn.active.value or 0)
            if act > tot:
                issues.append(ValidationIssue(
                    id="val_vpn_counts",
                    severity="ERROR",
                    field="vpn",
                    appendix_number=6,
                    message=f"Active VPN tunnels ({act}) cannot exceed total tunnels ({tot}).",
                    blocking=True
                ))
        except (ValueError, TypeError):
            pass

        # 4. Mandatory appendices presence
        mandatory_appendices = [
            (1, "CPU Usage"),
            (2, "Memory Usage"),
            (5, "Firmware Version"),
            (16, "Backup Configuration"),
        ]
        for app_num, name in mandatory_appendices:
            app_ev = pm.appendices.get(app_num)
            if not app_ev or not app_ev.screenshot_ids:
                issues.append(ValidationIssue(
                    id=f"val_missing_app_{app_num}",
                    severity="WARNING",
                    appendix_number=app_num,
                    message=f"Appendix {app_num} ({name}) does not have an assigned screenshot.",
                    blocking=False
                ))

        # 5. Hostname check
        if not pm.application.hostname.value:
            issues.append(ValidationIssue(
                id="val_missing_hostname",
                severity="WARNING",
                field="hostname",
                message="Firewall hostname is empty.",
                blocking=False
            ))

        # 6. Source-misfile / evidence mismatch validation warning
        for sc in session.screenshots:
            if sc.source_caption_category and sc.assigned_categories:
                if sc.source_caption_category not in sc.assigned_categories:
                    warn_msg = (
                        f"SOURCE_EVIDENCE_MISMATCH: Screenshot in Appendix {sc.source_appendix_number} "
                        f"('{sc.source_caption_category}') actually evidences "
                        f"{', '.join(sc.assigned_categories)}."
                    )
                    sc.mismatch_warning = warn_msg
                    issues.append(ValidationIssue(
                        id=f"val_source_mismatch_{sc.id}",
                        severity="WARNING",
                        field=sc.source_caption_category,
                        appendix_number=sc.source_appendix_number,
                        message=warn_msg,
                        blocking=False
                    ))

        return issues

consistency_validator = ConsistencyValidator()
