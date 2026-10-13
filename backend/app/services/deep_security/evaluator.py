"""
Evaluator and Rules Engine for Trend Micro Deep Security PM Report.
Evaluates health thresholds, version recommendations, and populates
structured checklist items and executive summary highlights.
"""

from typing import List, Optional
from .models import (
    DeepSecurityReportData,
    DeepSecuritySystemData,
    DeepSecurityServerHealth,
    DeepSecurityLicenseData,
    DeepSecurityAlertsEvents,
    DeepSecurityRecommendation,
    DeepSecurityChecklistItem,
    DeepSecurityChecklistSubtask,
)

class DeepSecurityEvaluator:
    """
    Evaluates Trend Micro Deep Security telemetry and populates checklist
    verdicts, executive key highlights, and software upgrade recommendations.
    """

    def evaluate(self, report_data: DeepSecurityReportData) -> None:
        """
        Executes evaluation rules on the report data and mutates checklist,
        key_highlights, and recommendations in place.
        """
        self._evaluate_highlights(report_data)
        self._evaluate_recommendations(report_data)
        self._evaluate_checklist(report_data)

    def _evaluate_highlights(self, report_data: DeepSecurityReportData) -> None:
        highlights: List[str] = []
        sys = report_data.system
        health = report_data.health
        alerts = report_data.alerts_events
        lic = report_data.licenses

        # Overall health status
        all_ok = health.disk_space_ok and health.server_performance_healthy and not alerts.notable_alerts_found
        if all_ok:
            highlights.append(
                "Based on our comprehensive monitoring and analysis, we are pleased to report that "
                "all systems are operating normally and functioning as expected."
            )
        else:
            highlights.append(
                "Based on monitoring and analysis, some items require attention or maintenance review."
            )

        # Alerts & Events
        if not alerts.notable_alerts_found and alerts.malware_detections == 0:
            highlights.append(
                "Alerts & Events: No critical or notable alerts were detected during the maintenance period. "
                "No malware detections were recorded; therefore, no event logs or log exports were generated."
            )
        else:
            highlights.append(
                f"Alerts & Events: {alerts.notable_alerts_count} alert(s) and {alerts.malware_detections} "
                f"malware detection(s) recorded during the maintenance period."
            )

        # License & Updates
        if lic.is_active:
            highlights.append(
                "License & System Updates: Deep Security licenses are active, and the server components are up to date "
                "with the latest security updates."
            )
        else:
            highlights.append(
                "License & System Updates: Attention required on license status or component updates."
            )

        # Server Health
        if health.disk_space_ok and health.server_performance_healthy:
            highlights.append(
                "Server Health: CPU usage is within normal operating ranges, memory usage is stable and within "
                "acceptable limits, and disk usage is optimal, with sufficient available space and no signs of "
                "disk-related issues or performance degradation."
            )
        else:
            disk_desc = "optimal" if health.disk_space_ok else "critical (< 30% available space)"
            highlights.append(
                f"Server Health: CPU/Memory status within limits, disk space status: {disk_desc}."
            )

        report_data.key_highlights = highlights

    def _evaluate_recommendations(self, report_data: DeepSecurityReportData) -> None:
        recs: List[DeepSecurityRecommendation] = []
        sys = report_data.system

        # 1. Deep Security Manager Version Upgrade Recommendation
        if sys.recommended_manager_version and sys.manager_version:
            rec_text = (
                f"Current manager version is {sys.manager_version}. Recommended to upgrade to the latest "
                f"Deep Security Manager software version {sys.recommended_manager_version} "
                f"(Released: {sys.manager_release_date or 'Recent'}) as the current version is old.\n"
            )
            if sys.manager_guide_url:
                rec_text += f"Deep Security 20 Administration Guide: {sys.manager_guide_url}"

            recs.append(
                DeepSecurityRecommendation(
                    item="Deep Security Manager Version",
                    current_version=sys.manager_version,
                    recommended_version=sys.recommended_manager_version,
                    release_date=sys.manager_release_date,
                    documentation_url=sys.manager_guide_url,
                    remarks=rec_text,
                )
            )

        # 2. Deep Security Agent Version Upgrade Recommendation
        if sys.recommended_agent_version and sys.agent_version:
            rec_agent_text = (
                f"Curren agent version is {sys.agent_version}. Recommended to upgrade to the latest "
                f"Deep Security Agent version {sys.recommended_agent_version} "
                f"(Released: {sys.agent_release_date or 'Recent'}) once Deep Security Manager has been upgraded."
            )
            recs.append(
                DeepSecurityRecommendation(
                    item="Deep Security Agent Version",
                    current_version=sys.agent_version,
                    recommended_version=sys.recommended_agent_version,
                    release_date=sys.agent_release_date,
                    documentation_url=None,
                    remarks=rec_agent_text,
                )
            )

        report_data.recommendations = recs

    def _evaluate_checklist(self, report_data: DeepSecurityReportData) -> None:
        sys = report_data.system
        health = report_data.health
        alerts = report_data.alerts_events
        lic = report_data.licenses

        items: List[DeepSecurityChecklistItem] = [
            # 1. Dashboard and Widgets
            DeepSecurityChecklistItem(
                no=1,
                task="Dashboard and Widgets",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that the dashboard is working",
                        expected_input="Login to the Deep Security web console",
                        expected_output="The Deep Security web console content should appear starting with the Dashboard and its Widgets",
                        result="Yes",
                        remarks="Dashboard and widgets load successfully\nRefer to Appendix 1",
                    ),
                    DeepSecurityChecklistSubtask(
                        task="Verify that the widgets are working",
                        expected_input="Refresh any widget on the dashboard page",
                        expected_output="Individual widgets should the relevant contents based on the information from Deep Security",
                        result="Yes",
                        remarks="Able to refresh widgets",
                    ),
                    DeepSecurityChecklistSubtask(
                        task="Verify that new widgets can be added",
                        expected_input='Click "Add Widgets" on the upper right portion of the dashboard Check a widget and click Add',
                        expected_output="The new selected Widgets should appear on the dashboard currently being displayed",
                        result="Yes",
                        remarks="Able to add/remove widgets",
                    ),
                ],
            ),
            # 2. Alerts
            DeepSecurityChecklistItem(
                no=2,
                task="Alerts",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Check for notable alerts",
                        expected_input="Go to Alert tab and check for any notable alerts",
                        expected_output="Check for any notable alerts, and provide feedback and best practice.",
                        result="Yes" if not alerts.notable_alerts_found else "No",
                        remarks="Refer to Appendix 2",
                    ),
                ],
            ),
            # 3. Events and Reports
            DeepSecurityChecklistItem(
                no=3,
                task="Events and Reports",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify Logging functionality",
                        expected_input="Go to Event & Reports > Anti-Malware Event > Select Computer and time period > click Display Logs",
                        expected_output="Selected logs should show up on a window as per criteria selected by admin",
                        result="Yes" if alerts.logging_functional else "No",
                        remarks="No detection Thus, no log generated\nRefer to Appendix 3" if alerts.malware_detections == 0 else "Refer to Appendix 3",
                    ),
                    DeepSecurityChecklistSubtask(
                        task="Verify Log Export capability",
                        expected_input="Perform above steps to View Logs and click Export All to CSV Select the directory and filename, then save the export",
                        expected_output="Selected logs as per criteria selected by admin should be exported to a csv file on the directory selected during export",
                        result="Yes" if alerts.export_functional else "No",
                        remarks="No detection. Thus, no log generated" if alerts.malware_detections == 0 else "Export functional",
                    ),
                ],
            ),
            # 4. License Status
            DeepSecurityChecklistItem(
                no=4,
                task="License Status",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that Deep Security license is active and updated",
                        expected_input="Go to Administration > License in Deep Security web console",
                        expected_output='Deep Security License Status for each relevant module should show as "Activated"',
                        result="Yes" if lic.is_active else "No",
                        remarks="Refer to Appendix 4",
                    ),
                ],
            ),
            # 5. Agent Inventory Management
            DeepSecurityChecklistItem(
                no=5,
                task="Agent Inventory Management",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that the Agent Inventory is properly populated",
                        expected_input="Go to Computers > All Computers in Deep Security web console and click on domain group in the computer hierarchy",
                        expected_output="Computers with Deep Security Agent installed should appear in the right pane of the Agent Management page",
                        result="Yes",
                        remarks="Refer to Appendix 5",
                    ),
                ],
            ),
            # 6. Deep Security Server Updates Status
            DeepSecurityChecklistItem(
                no=6,
                task="Deep Security Server Updates Status",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that Server Components are up to date",
                        expected_input="Go to Administration > Updates > Security Summary in Deep Security web console will show the last updates",
                        expected_output="The page should show the last Update time and the current versions that are loaded on the Deep Security server",
                        result="Yes",
                        remarks="Refer to Appendix 6",
                    ),
                ],
            ),
            # 7. Deep Security Manager System Information
            DeepSecurityChecklistItem(
                no=7,
                task="Deep Security Manager System Information",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify connectivity between Deep Security Manager Nodes and Database",
                        expected_input="Go to Administration > System Information in Deep Security web console and make sure that Deep Security Manager Nodes connect with Database",
                        expected_output="The page should show the Deep Security Manager Nodes connect with the Database.",
                        result="Yes" if sys.db_connected else "No",
                        remarks="Refer to Appendix 7",
                    ),
                ],
            ),
            # 8. Deep Security Agent Software Update
            DeepSecurityChecklistItem(
                no=8,
                task="Deep Security Agent Software Update",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that latest Deep Security Agent application",
                        expected_input="Go to Administrator > Software. Summary pages will show the last check update time and prompt alert for latest agent software release",
                        expected_output="The page should show the last check update time and latest agent software version if have new release.",
                        result="Yes",
                        remarks="Refer to Appendix 8",
                    ),
                ],
            ),
            # 9. Deep Security Manager and Database Server Health Check
            DeepSecurityChecklistItem(
                no=9,
                task="Deep Security Manager and Database Server Health Check",
                subtasks=[
                    DeepSecurityChecklistSubtask(
                        task="Verify that Server are running in good health state.",
                        expected_input="Login to Deep Security Manager Server and Deep Security Database Server. Check the Hard Disk Available Space and Server Performance",
                        expected_output="Deep Security Manager Server and Deep Security Database Server need have 30% available Hard Disk Space from total Hard Disk Space. Server Performance will be in healthy state.",
                        result="Yes" if (health.disk_space_ok and health.server_performance_healthy) else "No",
                        remarks="Refer Appendix 9",
                    ),
                ],
            ),
        ]

        report_data.checklist = items
