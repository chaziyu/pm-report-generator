"""
Manifest and metadata schemas for PM Report Dataset Importer.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ImageManifestEntry(BaseModel):
    source_part: str
    relationship_id: str
    width: Optional[int] = None
    height: Optional[int] = None
    classified_as: str = "appendix"  # appendix, decorative, signature, other
    appendix_number: Optional[int] = None
    saved_name: Optional[str] = None
    reason: Optional[str] = None

class AppendixManifestEntry(BaseModel):
    appendix: int
    title: str
    images: List[str] = Field(default_factory=list)
    mapping_confidence: float = 1.0
    source_appendix_number: Optional[int] = None
    source_appendix_caption: Optional[str] = None
    semantic_category: Optional[str] = None
    canonical_target_appendix: Optional[int] = None
    ground_truth_source: Optional[str] = None

class ReportManifest(BaseModel):
    case_id: str
    source_report: str
    source_sha256: str
    imported_at: str
    template_variant: str = "fortigate_pm_v1"
    images: List[ImageManifestEntry] = Field(default_factory=list)
    appendices: Dict[str, AppendixManifestEntry] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

class CaseIndexEntry(BaseModel):
    case_id: str
    report: str
    model: Optional[str] = None
    hostname: Optional[str] = None
    appendix_count: int = 0
    screenshot_count: int = 0
    warnings: int = 0
    source_sha256: str = ""

class DatasetIndex(BaseModel):
    cases: List[CaseIndexEntry] = Field(default_factory=list)

class ImportSummary(BaseModel):
    reports_scanned: int = 0
    reports_imported: int = 0
    reports_failed: int = 0
    duplicate_reports: int = 0
    appendices_found: int = 0
    appendices_missing: int = 0
    expected_fields_extracted: int = 0
    unresolved_fields: int = 0
    unsupported_template_variants: int = 0
