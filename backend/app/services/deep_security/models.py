"""
Data models for Trend Micro Deep Security PM Report.
Defines schemas for telemetry, server health, licensing, checklist items,
executive summary recommendations, and report data.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DeepSecuritySystemData(BaseModel):
    model: str = "Deep Security"
    hostname: str = "DSM-GF-MSER-01"
    manager_version: str = "20.0.844"
    recommended_manager_version: Optional[str] = "20.0.1160"
    manager_release_date: Optional[str] = "22 April 2026"
    manager_guide_url: Optional[str] = "https://help.deepsecurity.trendmicro.com/20_0/onpremise/Deep_Security_20_Administration_Guide.pdf"
    agent_version: Optional[str] = "20.0.0.8137"
    recommended_agent_version: Optional[str] = "20.0.3.8610"
    agent_release_date: Optional[str] = "15 April 2026"
    db_connected: bool = True
    dsm_ip: Optional[str] = "172.31.31.21"
    date_pm: Optional[str] = "20th May 2026"

class DeepSecurityServerHealth(BaseModel):
    cpu_usage_pct: Optional[float] = 3.0
    memory_usage_pct: Optional[float] = 31.0
    disk_free_pct: Optional[float] = 45.0
    disk_space_ok: bool = True  # True if >= 30% available disk space
    server_performance_healthy: bool = True

class DeepSecurityLicenseData(BaseModel):
    is_active: bool = True
    modules: List[str] = Field(
        default_factory=lambda: [
            "Anti-Malware",
            "Web Reputation",
            "Firewall",
            "Intrusion Prevention",
            "Integrity Monitoring",
            "Log Inspection",
        ]
    )

class DeepSecurityAlertsEvents(BaseModel):
    notable_alerts_found: bool = False
    notable_alerts_count: int = 0
    malware_detections: int = 0
    logging_functional: bool = True
    export_functional: bool = True

class DeepSecurityRecommendation(BaseModel):
    item: str
    current_version: Optional[str] = None
    recommended_version: Optional[str] = None
    release_date: Optional[str] = None
    documentation_url: Optional[str] = None
    remarks: str
    image_path: Optional[str] = None

class DeepSecurityChecklistSubtask(BaseModel):
    task: str
    expected_input: str
    expected_output: str
    result: str = "Yes"  # "Yes" or "No"
    remarks: str = ""

class DeepSecurityChecklistItem(BaseModel):
    no: int  # 1 to 9
    task: str
    subtasks: List[DeepSecurityChecklistSubtask] = Field(default_factory=list)

class DeepSecurityAppendixImage(BaseModel):
    appendix_no: int  # 1 to 9
    title: str
    image_path: str
    caption: Optional[str] = None

class DeepSecurityReportData(BaseModel):
    customer: str = "The Exchange TRX – LQ Retail Sdn Bhd"
    report_title: str = "Preventive Maintenance for Trend Micro Deep Security Report"
    fsms_id: str = "02892342"
    contract_no: str = "ISS/2025/M4170"
    contract_period: str = "01/04/2026 - 31/03/2027"
    pm_date: str = "20/05/2026"
    author_name: str = "Loh Zi Xin"
    author_designation: str = "Associate Technical Engineer"
    author_date: str = "20th May 2026"
    author_signature_text: Optional[str] = "ZiXin"
    author_signature_image: Optional[str] = None
    verified_name: str = "Fatin Amirah Binti Che A Latif"
    verified_designation: str = "Senior Technical Engineer"
    verified_date: str = "20th May 2026"
    verified_signature_image: Optional[str] = None
    system: DeepSecuritySystemData = Field(default_factory=DeepSecuritySystemData)
    health: DeepSecurityServerHealth = Field(default_factory=DeepSecurityServerHealth)
    licenses: DeepSecurityLicenseData = Field(default_factory=DeepSecurityLicenseData)
    alerts_events: DeepSecurityAlertsEvents = Field(default_factory=DeepSecurityAlertsEvents)
    key_highlights: List[str] = Field(default_factory=list)
    recommendations: List[DeepSecurityRecommendation] = Field(default_factory=list)
    checklist: List[DeepSecurityChecklistItem] = Field(default_factory=list)
    appendix_images: List[DeepSecurityAppendixImage] = Field(default_factory=list)
