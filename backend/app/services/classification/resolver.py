"""
Stage 2: AppendixAssignmentResolver
Resolves intended PM appendix assignment from Stage 1 detected categories.
Applies pairwise disambiguation, confidence margin calibration,
unknown classification for weak/insufficient evidence, and multi-label assignment.
"""

from typing import Dict, List, Tuple, Optional
from ...models.screenshot import ScreenshotRecord, ClassificationCandidate
from .evidence import EvidenceQuality, DetectedContentCategory

AUTO_CONFIRM_THRESHOLD = 0.85
REVIEW_REQUIRED_THRESHOLD = 0.65
MARGIN_CONFIRM_THRESHOLD = 0.08

class AppendixAssignmentResolver:
    """
    Stage 2 Resolver:
    Answers: 'Which appendix should this screenshot populate?'
    Uses detected content categories, evidence quality, category specificity,
    and pairwise disambiguation rules to decide primary assignment.
    """

    def resolve(
        self,
        detected: Dict[str, DetectedContentCategory],
        screenshot: ScreenshotRecord,
    ) -> Tuple[List[ClassificationCandidate], List[str], str, str]:
        """
        Returns:
            candidates: List of ClassificationCandidate sorted by confidence
            assigned_categories: List of confirmed categories (primary first)
            review_status: 'AUTO_CONFIRMED' or 'NEEDS_REVIEW'
            resolution_reason: Explanation of the resolution decision
        """
        # Filter categories that have at least minimal evidence
        active_items = [
            d for d in detected.values()
            if d.evidence_quality != EvidenceQuality.INSUFFICIENT and d.confidence >= 0.30
        ]

        if not active_items:
            return (
                [ClassificationCandidate(category="unknown", confidence=0.0, evidence_quality="INSUFFICIENT", reason="No category met minimum evidence requirements.")],
                [],
                "NEEDS_REVIEW",
                "No category met minimum evidence requirements. Marked unknown for review.",
            )

        # Apply pairwise disambiguation adjustments
        active_dict = {d.category: d for d in active_items}
        self._apply_pairwise_disambiguations(active_dict, screenshot)

        # Re-sort active categories by adjusted confidence
        sorted_cats = sorted(active_dict.values(), key=lambda d: (d.confidence, d.raw_score), reverse=True)

        # Calculate top-vs-second margin
        top = sorted_cats[0]
        second = sorted_cats[1] if len(sorted_cats) > 1 else None
        margin = round(top.confidence - (second.confidence if second else 0.0), 4)
        top.confidence_margin = margin

        # Check if top candidate qualifies as a confirmed category
        # If top candidate is WEAK or confidence is below review threshold, return unknown / review
        if top.evidence_quality == EvidenceQuality.WEAK and top.confidence < REVIEW_REQUIRED_THRESHOLD:
            return (
                [
                    ClassificationCandidate(
                        category="unknown",
                        confidence=0.0,
                        evidence_quality="INSUFFICIENT",
                        reason=f"Top candidate '{top.category}' has only weak/navigation evidence ({top.confidence}). Marked unknown for review.",
                    ),
                    self._to_candidate(top, margin),
                ],
                [],
                "NEEDS_REVIEW",
                f"Top candidate '{top.category}' has only weak/navigation evidence ({top.confidence}). Flagged for manual review.",
            )

        # Build candidate list
        candidates: List[ClassificationCandidate] = []
        for idx, item in enumerate(sorted_cats):
            item_margin = margin if idx == 0 else round(item.confidence - (sorted_cats[idx+1].confidence if idx+1 < len(sorted_cats) else 0.0), 4)
            candidates.append(self._to_candidate(item, item_margin))

        # Decide primary assignment and review status
        assigned: List[str] = [top.category]
        review_status = "NEEDS_REVIEW"
        reason = f"Primary category '{top.category}' assigned ({top.evidence_quality.value}, conf={top.confidence}, margin={margin})."

        # Determine auto-confirm eligibility
        if (
            top.evidence_quality in [EvidenceQuality.VERY_STRONG, EvidenceQuality.STRONG]
            and top.confidence >= AUTO_CONFIRM_THRESHOLD
            and margin >= MARGIN_CONFIRM_THRESHOLD
        ):
            review_status = "AUTO_CONFIRMED"
            reason += " High evidence quality and margin met auto-confirm threshold."
        elif top.confidence < AUTO_CONFIRM_THRESHOLD:
            review_status = "NEEDS_REVIEW"
            reason += " Confidence below auto-confirm threshold; manual verification recommended."
        else:
            review_status = "NEEDS_REVIEW"
            reason += f" Competing candidate '{second.category if second else ''}' within close margin ({margin}). Flagged for review."

        # Support valid multi-category co-location (e.g. Firmware + Uptime, GUI + CPU/Memory)
        for c in sorted_cats[1:]:
            if c.confidence >= AUTO_CONFIRM_THRESHOLD and c.evidence_quality in [EvidenceQuality.VERY_STRONG, EvidenceQuality.STRONG]:
                # Don't add mutually conflicting CPU and Memory simultaneously as top assignments unless both strong
                if (top.category == "cpu_usage" and c.category == "memory_usage") or \
                   (top.category == "memory_usage" and c.category == "cpu_usage"):
                    continue
                if c.category not in assigned:
                    assigned.append(c.category)

        return candidates, assigned, review_status, reason

    def _apply_pairwise_disambiguations(
        self,
        active_dict: Dict[str, DetectedContentCategory],
        screenshot: ScreenshotRecord,
    ) -> None:
        """Applies domain-specific semantic disambiguation rules between known confusing pairs."""
        raw_text = (screenshot.ocr_text or "").lower()

        # 0. cpu_usage vs memory_usage tie-breaking
        if "cpu_usage" in active_dict and "memory_usage" in active_dict:
            has_cpu_text = "cpu" in raw_text or "processor" in raw_text
            has_mem_text = "memory" in raw_text or "mem" in raw_text or "ram" in raw_text
            is_full_dashboard = "dashboard" in raw_text and ("+ add widget" in raw_text or "add widget" in raw_text or "/system/dashboard" in raw_text)
            if not is_full_dashboard:
                if has_cpu_text and not ("memory" in raw_text or "ram" in raw_text):
                    active_dict["cpu_usage"].confidence = min(0.98, max(active_dict["cpu_usage"].confidence, 0.95))
                    active_dict["cpu_usage"].evidence_quality = EvidenceQuality.VERY_STRONG
                    active_dict["memory_usage"].confidence = max(0.35, active_dict["memory_usage"].confidence - 0.30)
                elif has_mem_text and not ("cpu" in raw_text or "processor" in raw_text):
                    active_dict["memory_usage"].confidence = min(0.98, max(active_dict["memory_usage"].confidence, 0.95))
                    active_dict["memory_usage"].evidence_quality = EvidenceQuality.VERY_STRONG
                    active_dict["cpu_usage"].confidence = max(0.35, active_dict["cpu_usage"].confidence - 0.30)

        # 1. firmware_version vs system_uptime
        if "firmware_version" in active_dict and "system_uptime" in active_dict:
            fw = active_dict["firmware_version"]
            ut = active_dict["system_uptime"]
            has_uptime_regex = len(ut.regex_matches) > 0 or any(
                term in raw_text for term in ["days,", "hours,", "day(s)", "hour(s)", "51d", "76b", "177d", "36m", "44m"]
            )
            has_fw_url = any("/firmware" in u for u in fw.url_matches) or "/system/firmware" in raw_text
            if has_fw_url:
                fw.confidence = min(0.98, fw.confidence + 0.05)
                ut.confidence = max(0.50, ut.confidence - 0.20)
            elif has_uptime_regex and not has_fw_url:
                ut.confidence = min(0.98, max(ut.confidence, 0.95))
                ut.evidence_quality = EvidenceQuality.VERY_STRONG

        # 2. gui_access vs specific resource widgets
        if "gui_access" in active_dict:
            gui = active_dict["gui_access"]
            has_dashboard_url = any("/system/dashboard" in u or "/ng/dashboard" in u or "dashboard/1" in u for u in gui.url_matches) or "/system/dashboard" in raw_text
            has_add_widget = "+ add widget" in raw_text or "add widget" in raw_text or "dashboard status" in raw_text
            is_full_dashboard = has_dashboard_url or (has_add_widget and len(active_dict) >= 3)

            if is_full_dashboard:
                gui.confidence = min(0.98, max(gui.confidence, 0.96))
                gui.evidence_quality = EvidenceQuality.VERY_STRONG
                for res_cat in ["cpu_usage", "memory_usage", "firmware_version", "system_uptime", "license_info"]:
                    if res_cat in active_dict and res_cat != "gui_access":
                        active_dict[res_cat].confidence = min(active_dict[res_cat].confidence, 0.88)
            else:
                for res_cat in ["cpu_usage", "memory_usage"]:
                    if res_cat in active_dict:
                        res = active_dict[res_cat]
                        if res.evidence_quality in [EvidenceQuality.VERY_STRONG, EvidenceQuality.STRONG]:
                            if res.confidence >= gui.confidence:
                                gui.confidence = max(0.60, gui.confidence - 0.10)

        # 3. interface vs routing_table
        if "interface" in active_dict and "routing_table" in active_dict:
            iface = active_dict["interface"]
            route = active_dict["routing_table"]
            has_routing_markers = (
                len(route.regex_matches) > 0
                or any(t in raw_text for t in ["gateway", "distance", "metric", "static route", "routing monitor", "destination", "fib"])
            )
            has_physical_iface = any(
                t in raw_text for t in ["physical interface", "link status", "speed", "duplex", "faceplate", "aggregate"]
            )
            if has_routing_markers and not has_physical_iface:
                route.confidence = min(0.98, route.confidence + 0.08)
                iface.confidence = max(0.50, iface.confidence - 0.15)
            elif has_physical_iface and not has_routing_markers:
                iface.confidence = min(0.98, iface.confidence + 0.08)
                route.confidence = max(0.50, route.confidence - 0.15)

        # 4. ha_status vs cli_access
        if "ha_status" in active_dict and "cli_access" in active_dict:
            ha = active_dict["ha_status"]
            cli = active_dict["cli_access"]
            is_get_system_status = any(
                t in raw_text for t in ["get system status", "get system stat", "virus-db", "bios version", "first ga patch", "branch point"]
            )
            has_ha_command = any(
                t in raw_text for t in ["get system ha status", "get system ha", "mode: a-p", "active-passive", "ha cluster", "standalone mode", "ha group", "cluster members"]
            )
            has_ha_gui = any("/system/ha" in u for u in ha.url_matches) or "/system/ha" in raw_text or "high availability" in raw_text

            if is_get_system_status and not has_ha_command:
                cli.confidence = min(0.98, max(cli.confidence, 0.95))
                cli.evidence_quality = EvidenceQuality.VERY_STRONG
                ha.confidence = max(0.40, ha.confidence - 0.25)
            elif has_ha_command or has_ha_gui:
                ha.confidence = min(0.98, max(ha.confidence, 0.92))
                ha.evidence_quality = EvidenceQuality.VERY_STRONG
                cli.confidence = max(0.50, cli.confidence - 0.20)

        # 5. system_event vs log_manager
        if "system_event" in active_dict and "log_manager" in active_dict:
            se = active_dict["system_event"]
            lm = active_dict["log_manager"]
            has_event_table = any(t in raw_text for t in ["system events", "event-log", "event severity", "critical", "warning", "sub type", "log id"])
            has_remote_log = any(t in raw_text for t in ["log settings", "fortianalyzer", "syslog server", "remote log", "logging & analytics", "disk logging"])
            if has_event_table and not has_remote_log:
                se.confidence = min(0.98, se.confidence + 0.08)
                lm.confidence = max(0.50, lm.confidence - 0.15)
            elif has_remote_log and not has_event_table:
                lm.confidence = min(0.98, lm.confidence + 0.08)
                se.confidence = max(0.50, se.confidence - 0.15)

        # 6. backup_configuration vs system_event / log_manager / cli_access
        if "backup_configuration" in active_dict:
            bk = active_dict["backup_configuration"]
            has_config_cli = any(
                t in raw_text for t in ["config system", "config firewall", "config router", "config switch", "set hostname", "set uuid", "end\nconfig", "end\r\nconfig"]
            )
            has_backup_dialog = any(
                t in raw_text for t in ["backup system configuration", "backup to", "download", ".conf", "restore system"]
            )
            is_log_settings = "/log/settings" in raw_text or "log settings" in raw_text or "threat weight" in raw_text
            if is_log_settings and not (has_config_cli or has_backup_dialog):
                bk.confidence = max(0.30, bk.confidence - 0.35)
            elif has_config_cli or has_backup_dialog:
                bk.confidence = min(0.98, max(bk.confidence, 0.92))
                bk.evidence_quality = EvidenceQuality.VERY_STRONG
                for other_cat in ["system_event", "log_manager", "cli_access"]:
                    if other_cat in active_dict:
                        active_dict[other_cat].confidence = max(0.40, active_dict[other_cat].confidence - 0.25)

        # 7. firewall_datetime vs backup_configuration / log_manager / firmware_version
        if "firewall_datetime" in active_dict:
            dt = active_dict["firewall_datetime"]
            has_dt_url = any("/system/settings" in u or "/system/time" in u for u in dt.url_matches) or "/system/settings" in raw_text
            has_dt_content = any(t in raw_text for t in ["time zone", "system time", "ntp server", "time synchronization", "synchronized with ntp", "daylight saving"])
            if (has_dt_url or has_dt_content) and dt.confidence >= 0.70:
                dt.confidence = min(0.98, max(dt.confidence, 0.94))
                dt.evidence_quality = EvidenceQuality.VERY_STRONG
                for other_cat in ["backup_configuration", "log_manager"]:
                    if other_cat in active_dict:
                        active_dict[other_cat].confidence = max(0.40, active_dict[other_cat].confidence - 0.25)

        # 8. routing_table vs log_manager
        if "routing_table" in active_dict and "log_manager" in active_dict:
            route = active_dict["routing_table"]
            lm = active_dict["log_manager"]
            has_route_url = any("/routing" in u for u in route.url_matches) or "/routing" in raw_text or "/ng/routing" in raw_text
            has_route_content = any(t in raw_text for t in ["static route", "routing monitor", "destination", "gateway ip", "fib routes"]) or len(route.regex_matches) > 0
            if (has_route_url or has_route_content) and route.confidence >= 0.70:
                route.confidence = min(0.98, max(route.confidence, 0.94))
                route.evidence_quality = EvidenceQuality.VERY_STRONG
                lm.confidence = max(0.40, lm.confidence - 0.25)

        # 9. cli_access vs firmware_version (e.g. get system status command output)
        if "cli_access" in active_dict and "firmware_version" in active_dict:
            cli = active_dict["cli_access"]
            fw = active_dict["firmware_version"]
            is_cli_output = any(
                t in raw_text for t in ["virus-db", "bios version", "first ga patch", "branch point", "last reboot reason", "system part-number", "command parse error", "command fail"]
            )
            has_fw_url = any("/firmware" in u for u in fw.url_matches) or "/system/firmware" in raw_text
            if is_cli_output and not has_fw_url:
                cli.confidence = min(0.98, max(cli.confidence, 0.96))
                cli.evidence_quality = EvidenceQuality.VERY_STRONG
                fw.confidence = max(0.40, fw.confidence - 0.25)

        # 10. system_event vs license_info (e.g. event log table mentioning FortiToken)
        if "system_event" in active_dict and "license_info" in active_dict:
            se = active_dict["system_event"]
            lic = active_dict["license_info"]
            has_event_markers = any("/log/event" in u for u in se.url_matches) or "/log/event" in raw_text or any(
                t in raw_text for t in ["date/time", "event log", "system events", "log description", "sub type", "event severity", "performance statistics:"]
            )
            has_lic_url = any("/license" in u or "/forticare" in u for u in lic.url_matches) or "/system/license" in raw_text
            if has_event_markers and not has_lic_url:
                se.confidence = min(0.98, max(se.confidence, 0.95))
                se.evidence_quality = EvidenceQuality.VERY_STRONG
                lic.confidence = max(0.40, lic.confidence - 0.30)

    def _to_candidate(self, item: DetectedContentCategory, margin: float) -> ClassificationCandidate:
        return ClassificationCandidate(
            category=item.category,
            confidence=item.confidence,
            raw_score=item.raw_score,
            evidence_quality=item.evidence_quality.value,
            strong_anchors_matched=item.strong_anchors_matched,
            supporting_anchors_matched=item.supporting_anchors_matched,
            negative_anchors_matched=item.negative_anchors_matched,
            regex_matches=item.regex_matches,
            url_matches=item.url_matches,
            navigation_matches=item.navigation_matches,
            confidence_margin=margin,
            reason=item.reason,
        )

resolver = AppendixAssignmentResolver()
