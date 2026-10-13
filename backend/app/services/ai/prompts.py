"""
Fixed Prompt Templates for Qwen3-1.7B Local AI inference.
Enforces strict JSON schema instructions and identity protection rules.
"""

from typing import List

ALLOWED_CATEGORIES: List[str] = [
    "cpu_usage",
    "memory_usage",
    "interface",
    "license_info",
    "firmware_version",
    "vpn_tunnels",
    "routing_table",
    "system_uptime",
    "gui_access",
    "cli_access",
    "signature_version",
    "firewall_datetime",
    "ha_status",
    "system_event",
    "log_manager",
    "backup_configuration",
    "unknown",
]

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert FortiGate firewall telemetry classifier.
Your task is to analyze extracted OCR text from a screenshot and determine which Preventive Maintenance (PM) categories are genuinely evidenced.
A screenshot may contain evidence for MULTIPLE categories (for example, a dashboard widget showing both firmware and uptime, or a full dashboard overview showing GUI access and CPU usage).

ALLOWED CATEGORIES:
""" + "\n".join(f"- {cat}" for cat in ALLOWED_CATEGORIES) + """

RULES:
1. Only mark evidenced=true if unambiguous keywords or data for that category appear in the OCR text.
2. DO NOT hallucinate or guess categories that are not supported by the OCR text.
3. Respond ONLY with valid, raw JSON matching this schema:
{
  "categories": [
    {"category": "category_name", "evidenced": true, "confidence": 0.95, "reason": "brief reason"}
  ],
  "primary_category": "most_prominent_category",
  "is_multi_category": true
}
"""

def build_classification_prompt(ocr_text: str, candidate_categories: List[str]) -> str:
    prompt = f"CANDIDATE HINTS FROM DETERMINISTIC CLASSIFIER: {', '.join(candidate_categories) if candidate_categories else 'None'}\n\n"
    prompt += "OCR TEXT FROM SCREENSHOT:\n"
    prompt += "----------------------------------------\n"
    # Limit to first 3000 chars to fit within context
    prompt += ocr_text[:3000].strip() + "\n"
    prompt += "----------------------------------------\n"
    prompt += "Which PM categories are actually evidenced by this OCR? Return JSON only:"
    return prompt

EXTRACTION_SYSTEM_PROMPT = """You are a precise telemetry value parser for FortiGate firewalls.
Your task is to extract operational telemetry values strictly from the provided OCR text.

CRITICAL IDENTITY AND SAFETY RULES:
1. For hostnames, serial numbers (primary or secondary), and IP addresses:
   DO NOT reconstruct, guess, or fix missing characters.
   Return ONLY verbatim substrings supported directly by the OCR text.
2. For serial numbers:
   - 'application.serial_primary' is the serial of the primary/master device.
   - 'application.serial_secondary' is the serial of the secondary/slave/standby device.
   If only one serial number appears or no secondary serial is explicitly evidenced, set 'application.serial_secondary' to null. NEVER duplicate the primary serial into serial_secondary.
3. If a field value is not explicitly evidenced in the OCR text, you MUST set its value to null.
4. Respond ONLY with valid, raw JSON matching this schema:
{
  "fields": {
    "field_path": {"field_path": "field_path", "value": "extracted_val_or_null", "confidence": 0.95, "source_evidence": "snippet_or_null"}
  }
}
"""

def build_extraction_prompt(ocr_text: str, requested_fields: List[str]) -> str:
    prompt = f"TARGET FIELDS TO EXTRACT:\n"
    for f in requested_fields:
        prompt += f"- {f}\n"
    prompt += "\nOCR TEXT:\n"
    prompt += "----------------------------------------\n"
    prompt += ocr_text[:3000].strip() + "\n"
    prompt += "----------------------------------------\n"
    prompt += "Extract the requested fields. Return JSON only:"
    return prompt

# =====================================================================
# CheckPoint Vendor PM & CTC Conversion Prompts
# =====================================================================

CHECKPOINT_VENDOR_PM_SYSTEM_PROMPT = """You are an expert CheckPoint Firewall Telemetry & PM Report Analyst.
Your task is to analyze extracted text or OCR from a vendor Preventive Maintenance (PM) report and extract structured operational telemetry into raw JSON.

CRITICAL EXTRACTION RULES:
1. Extract verbatim values for hostname, model, MAC, OS, Check Point version, uptime, and management IP.
2. Carefully inspect storage/disk utilization:
   - Identify whether /var/log or any partition is >= 80% or critical.
   - Detect whether log switch is enabled or disabled.
3. Identify backup status and NTP synchronization configuration.
4. Extract all recommendations (item name and remarks).
5. Respond ONLY with valid, raw JSON matching this schema:
{
  "system": {
    "hostname": "Ki-L10-B2-FW01",
    "model": "Check Point 6900",
    "os_version": "Linux 4.18.0-372.9.1cpx86_64",
    "cp_version": "R82 - Build 016",
    "uptime": "82 days",
    "mgmt_ip": "10.42.2.253",
    "is_gateway": true
  },
  "storage_log": {
    "var_log_full": false,
    "max_disk_used_pct": 39,
    "log_switch_enabled": true
  },
  "recommendations": [
    {"item": "Backup setting", "remarks": "..."}
  ],
  "key_highlights": [
    "The overall system is operating in a healthy and stable condition."
  ]
}
"""

def build_checkpoint_vendor_pm_prompt(vendor_report_text: str) -> str:
    prompt = "VENDOR PM REPORT TEXT:\n"
    prompt += "----------------------------------------\n"
    prompt += vendor_report_text[:4000].strip() + "\n"
    prompt += "----------------------------------------\n"
    prompt += "Extract structured CheckPoint telemetry and recommendations. Return JSON only:"
    return prompt

# =====================================================================
# Trend Micro Deep Security PM Conversion & Interpretation Prompts
# =====================================================================

DEEP_SECURITY_ALLOWED_CATEGORIES: List[str] = [
    "dashboard_widgets",
    "alerts",
    "events_reports",
    "license_status",
    "agent_inventory",
    "server_updates",
    "system_information",
    "agent_software_update",
    "server_health",
]

DEEP_SECURITY_PM_SYSTEM_PROMPT = """You are an expert Trend Micro Deep Security Telemetry & Preventive Maintenance Analyst.
Your task is to analyze extracted OCR text or operational logs from a Deep Security environment and extract structured telemetry, health indicators, checklist verdicts, and upgrade recommendations into raw JSON.

CRITICAL RULES:
1. Extract verbatim identifiers for hostname, manager version, agent version, and server IP.
2. Evaluate server health (CPU, Memory, Disk Space). Confirm whether disk space has >= 30% available space.
3. Check for notable alerts or anti-malware detections.
4. Check whether Deep Security licenses for relevant modules (Anti-Malware, Web Reputation, Firewall, etc.) are "Activated".
5. Detect software version updates: if manager or agent versions have newer releases, generate corresponding recommendations.
6. Respond ONLY with valid, raw JSON matching this schema:
{
  "system": {
    "hostname": "DSM-GF-MSER-01",
    "model": "Deep Security",
    "manager_version": "20.0.844",
    "agent_version": "20.0.0.8137",
    "db_connected": true
  },
  "health": {
    "cpu_usage_pct": 3.0,
    "memory_usage_pct": 31.0,
    "disk_space_ok": true,
    "server_performance_healthy": true
  },
  "licenses": {
    "is_active": true
  },
  "alerts_events": {
    "notable_alerts_found": false,
    "malware_detections": 0
  },
  "recommendations": [
    {
      "item": "Deep Security Manager Version",
      "remarks": "Current manager version is 20.0.844. Recommended to upgrade to 20.0.1160."
    }
  ],
  "key_highlights": [
    "All systems are operating normally and functioning as expected."
  ]
}
"""

def build_deep_security_pm_prompt(report_text: str) -> str:
    prompt = "DEEP SECURITY EVIDENCE TEXT:\n"
    prompt += "----------------------------------------\n"
    prompt += report_text[:4000].strip() + "\n"
    prompt += "----------------------------------------\n"
    prompt += "Extract structured Deep Security telemetry, health checks, and recommendations. Return JSON only:"
    return prompt


