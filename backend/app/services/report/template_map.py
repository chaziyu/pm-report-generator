"""
Template mapping for FortiGate Preventive Maintenance DOCX Report.
Derived directly from empirical analysis of templates/preventive-maintenance.docx.
Provides stable semantic locator helpers rather than fragile absolute offsets.
"""

from typing import Dict, Any, List

APPENDIX_MAP: Dict[str, int] = {
    "cpu_usage": 1,
    "memory_usage": 2,
    "interface": 3,
    "license_info": 4,
    "firmware_version": 5,
    "vpn_tunnels": 6,
    "routing_table": 7,
    "system_uptime": 8,
    "gui_access": 9,
    "cli_access": 10,
    "signature_version": 11,
    "firewall_datetime": 12,
    "ha_status": 13,
    "system_event": 14,
    "log_manager": 15,
    "backup_configuration": 16,
}

REVERSE_APPENDIX_MAP: Dict[int, str] = {v: k for k, v in APPENDIX_MAP.items()}

# Appendix table and cell locators in preventive-maintenance.docx
# Allows finding the exact container paragraph and image slot
APPENDIX_LOCATORS: Dict[int, Dict[str, Any]] = {
    1: {
        "caption": "Appendix 1-CPU Usage",
        "table_idx": 10,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId39"],
        "max_images": 1,
    },
    2: {
        "caption": "Appendix 2 – Memory Usage",
        "table_idx": 10,
        "row_idx": 1,
        "col_idx": 0,
        "embed_rids": ["rId40"],
        "max_images": 1,
    },
    3: {
        "caption": "Appendix 3 – Interface",
        "table_idx": 11,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId41", "rId42", "rId43", "rId44"],
        "max_images": 4,
    },
    4: {
        "caption": "Appendix 4 – License Info",
        "table_idx": 11,
        "row_idx": 1,
        "col_idx": 0,
        "embed_rids": ["rId45"],
        "max_images": 1,
    },
    5: {
        "caption": "Appendix 5 – Firmware Version",
        "table_idx": 11,
        "row_idx": 2,
        "col_idx": 0,
        "embed_rids": ["rId46"],
        "max_images": 1,
    },
    6: {
        "caption": "Appendix 6 – VPN Tunnels",
        "table_idx": 11,
        "row_idx": 3,
        "col_idx": 0,
        "embed_rids": ["rId47"],
        "max_images": 1,
    },
    7: {
        "caption": "Appendix 7 – Static Routes & Routing Table",
        "table_idx": 12,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId48", "rId49", "rId50", "rId51", "rId52"],
        "max_images": 5,
    },
    8: {
        "caption": "Appendix 8 – Firewall System Uptime",
        "table_idx": 12,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId53"],
        "max_images": 1,
    },
    9: {
        "caption": "Appendix 9 – Accessed via GUI",
        "table_idx": 12,
        "row_idx": 1,
        "col_idx": 0,
        "embed_rids": ["rId54"],
        "max_images": 1,
    },
    10: {
        "caption": "Appendix 10 – Accessed via CLI/SSH",
        "table_idx": 13,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId55"],
        "max_images": 1,
    },
    11: {
        "caption": "Appendix 11 – Signatures Version",
        "table_idx": 14,
        "row_idx": 0,
        "col_idx": 0,
        "embed_rids": ["rId56", "rId57", "rId58"],
        "max_images": 3,
    },
    12: {
        "caption": "Appendix 12 – Firewall Date & Time",
        "table_idx": 14,
        "row_idx": 1,
        "col_idx": 0,
        "embed_rids": ["rId59"],
        "max_images": 1,
    },
    13: {
        "caption": "Appendix 13 – HA Status",
        "table_idx": 14,
        "row_idx": 2,
        "col_idx": 0,
        "embed_rids": ["rId60"],
        "max_images": 1,
    },
    14: {
        "caption": "Appendix 14 - System Event",
        "table_idx": 14,
        "row_idx": 3,
        "col_idx": 0,
        "embed_rids": ["rId61"],
        "max_images": 1,
    },
    15: {
        "caption": "Appendix 15 – Log Manager Setting",
        "table_idx": 14,
        "row_idx": 4,
        "col_idx": 0,
        "embed_rids": ["rId62"],
        "max_images": 1,
    },
    16: {
        "caption": "Appendix 16 – Backup Configuration",
        "table_idx": 14,
        "row_idx": 5,
        "col_idx": 0,
        "embed_rids": ["rId63"],
        "max_images": 1,
    },
}

# Semantic descriptors for table cells in the report body
TABLE_MAPPINGS: Dict[str, Any] = {
    "application_information": {
        "table_idx": 2,
        "fields": {
            "model": {"row": 0, "col": 1},
            "hostname": {"row": 1, "col": 1},
            "serial_number": {"row": 2, "col": 1},
        }
    },
    "hardware_health": {
        "table_idx": 4,
        "rows": {
            "disk": {"row": 1, "status_col": 3, "remarks_col": 4, "options": ["Healthy", "Unhealthy", "N/A"]},
            "cpu": {"row": 2, "status_col": 3, "remarks_col": 4, "options": ["Healthy", "Unhealthy", "N/A"]},
            "memory": {"row": 3, "status_col": 3, "remarks_col": 4, "options": ["Healthy", "Unhealthy", "N/A"]},
            "interface": {"row": 4, "status_col": 3, "remarks_col": 4, "options": ["Healthy", "Unhealthy", "N/A"]},
        }
    },
    "licensing": {
        "table_idx": 5,
        "rows": {
            "forticare": {"row": 1, "status_col": 3, "remarks_col": 4, "options": ["Valid", "Expired", "N/A"]},
            "utm_bundle": {"row": 2, "status_col": 3, "remarks_col": 4, "options": ["Valid", "Expired", "N/A"]},
        }
    },
    "firmware": {
        "table_idx": 6,
        "rows": {
            "firmware_version": {"row": 1, "status_col": 3, "remarks_col": 4, "options": ["Up-to-Date", "Out-of-Date"]},
            "ffr": {"row": 2, "status_col": 3, "remarks_col": 4, "options": ["Valid", "Expired", "N/A"]},
            "eos": {"row": 3, "status_col": 3, "remarks_col": 4, "options": ["Valid", "Expired", "N/A"]},
        }
    },
    "vpn": {
        "table_idx": 7,
        "rows": {
            "tunnel_count": {"row": 1, "status_col": 3, "remarks_col": 4},
        }
    },
    "routing": {
        "table_idx": 8,
        "rows": {
            "routing_table": {"row": 1, "status_col": 3, "remarks_col": 4},
        }
    },
    "configuration": {
        "table_idx": 9,
        "rows": {
            "uptime": {"row": 1, "status_col": 3, "remarks_col": 4},
            "gui_access": {"row": 2, "status_col": 3, "remarks_col": 4, "options": ["Pass", "Failed", "N/A"]},
            "cli_access": {"row": 3, "status_col": 3, "remarks_col": 4, "options": ["Pass", "Failed", "N/A"]},
            "signature_version": {"row": 4, "status_col": 3, "remarks_col": 4, "options": ["Up-to-Date", "Out-of-Date"]},
            "datetime": {"row": 5, "status_col": 3, "remarks_col": 4, "options": ["Pass", "Failed", "N/A"]},
            "internet_access": {"row": 6, "status_col": 3, "remarks_col": 4, "options": ["Pass", "Failed", "N/A"]},
            "ha_status": {"row": 7, "status_col": 3, "remarks_col": 4, "options": ["Pass", "Failed", "N/A"]},
            "event_logging": {"row": 8, "status_col": 3, "remarks_col": 4, "options": ["Available", "Un-available"]},
            "log_manager": {"row": 9, "status_col": 3, "remarks_col": 4, "options": ["Healthy", "Unhealthy", "N/A"]},
            "backup": {"row": 10, "status_col": 3, "remarks_col": 4, "options": ["Passed", "Failed"]},
        }
    }
}
