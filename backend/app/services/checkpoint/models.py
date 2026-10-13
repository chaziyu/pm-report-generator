from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CheckPointSystemInfo(BaseModel):
    hostname: str = ""
    mac_address: str = ""
    model: str = ""
    config_mode: str = ""
    os_version: str = ""
    cp_version: str = ""
    jumbo_hotfix: str = ""
    uptime: str = ""
    serial: Optional[str] = None
    mgmt_ip: Optional[str] = None
    date_pm: Optional[str] = None
    is_gateway: bool = True

class CheckPointHardwareInfo(BaseModel):
    ram: str = ""
    swap: str = ""
    cpu_specs: str = ""
    active_interfaces: int = 0
    inactive_interfaces: int = 0
    psu_status: str = "OK"
    sensors: Dict[str, Any] = Field(default_factory=dict)

class CheckPointNetworkInfo(BaseModel):
    interfaces: List[Dict[str, str]] = Field(default_factory=list)
    routing_entries: List[Dict[str, str]] = Field(default_factory=list)
    dns_servers: List[str] = Field(default_factory=list)
    domain: Optional[str] = None

class CheckPointStorageLogInfo(BaseModel):
    disk_partitions: List[Dict[str, Any]] = Field(default_factory=list)
    var_log_full: bool = False
    max_disk_used_pct: int = 0
    log_dir: str = "$FWDIR/log"
    var_log_size: str = ""
    log_files_size: str = ""
    delete_threshold: str = ""
    alert_threshold: str = ""
    log_switch_size: str = ""
    log_switch_enabled: bool = True

class CheckPointDateTimeInfo(BaseModel):
    current_system_time: str = ""
    actual_local_time: str = ""
    ntp_enabled: bool = True
    ntp_server_ip: str = ""
    ntp_type: str = ""
    ntp_version: str = ""
    timezone_correct: bool = True

class CheckPointBackupInfo(BaseModel):
    backup_enabled: bool = False
    schedule_name: str = "-"
    backup_type: str = "-"
    recur: str = "-"
    start_time: str = "-"
    location: str = "-"

class CheckPointLicenseInfo(BaseModel):
    host: str = ""
    expiration: str = ""
    signature: str = ""
    features: List[str] = Field(default_factory=list)
    is_valid: bool = True

class CheckPointPerformanceInfo(BaseModel):
    cpu_core_utilizations: List[float] = Field(default_factory=list)
    avg_cpu_utilization: float = 0.0
    memory_utilization_pct: float = 0.0
    swap_utilization_pct: float = 0.0
    current_connections: Optional[int] = None
    peak_connections: Optional[int] = None
    interface_errors: List[Dict[str, Any]] = Field(default_factory=list)

class CheckPointRecommendation(BaseModel):
    item: str = ""
    remarks: str = ""

class CheckPointChecklistItem(BaseModel):
    no: int
    description: str
    expected_result: str
    pass_status: str  # "Y", "N", "N/A"
    remarks: str

class CheckPointAppendixImage(BaseModel):
    appendix_no: int
    appendix_title: str
    image_path: str
    section_tag: str
    page_number: int
    width_in_inches: float = 6.0

class CheckPointDeviceData(BaseModel):
    system: CheckPointSystemInfo = Field(default_factory=CheckPointSystemInfo)
    hardware: CheckPointHardwareInfo = Field(default_factory=CheckPointHardwareInfo)
    network: CheckPointNetworkInfo = Field(default_factory=CheckPointNetworkInfo)
    storage_log: CheckPointStorageLogInfo = Field(default_factory=CheckPointStorageLogInfo)
    datetime_info: CheckPointDateTimeInfo = Field(default_factory=CheckPointDateTimeInfo)
    backup: CheckPointBackupInfo = Field(default_factory=CheckPointBackupInfo)
    license: CheckPointLicenseInfo = Field(default_factory=CheckPointLicenseInfo)
    performance: CheckPointPerformanceInfo = Field(default_factory=CheckPointPerformanceInfo)
    recommendations: List[CheckPointRecommendation] = Field(default_factory=list)
    recommendation_crop_path: Optional[str] = None
    key_highlights: List[str] = Field(default_factory=list)
    checklist: List[CheckPointChecklistItem] = Field(default_factory=list)
    appendix_images: List[CheckPointAppendixImage] = Field(default_factory=list)

class CheckPointReportData(BaseModel):
    customer: str = "CIMB BANK BERHAD"
    report_title: str = "3rd Quarter Of 2026 Preventive Maintenance Report For Check Point Firewall"
    pm_period: str = "3rd Quarter 2026"
    author_name: str = "Cha Zi Yu"
    author_designation: str = "Associate Technical Engineer"
    prepared_by: str = "CTC Global Sdn Bhd"
    devices: List[CheckPointDeviceData] = Field(default_factory=list)
