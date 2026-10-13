import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf

from .models import (
    CheckPointDeviceData,
    CheckPointAppendixImage,
)

class CheckpointSectionCropper:
    """
    Renders and crops high-resolution section evidence from CheckPoint Vendor PM PDF reports,
    mapping them directly to CTC standard appendices and executive summary recommendations.
    """

    def __init__(self, dpi: int = 150):
        self.dpi = dpi

    def crop_device_evidence(
        self,
        pdf_path: Path,
        device: CheckPointDeviceData,
        output_dir: Path
    ) -> None:
        """
        Extracts cropped appendix images and recommendation tables for a device,
        updating device.appendix_images and device.recommendation_crop_path.
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(str(pdf_path))
        is_gw = device.system.is_gateway

        # Map target headings
        heading_patterns = [
            "1.1 System Information",
            "1.2 Hardware Information",
            "1.3 Hardware Sensors",
            "1.4 Interface information",
            "1.5 Routing information",
            "1.6 Domain Name Service Information",
            "1.7 Firewall System Date and Time",
            "1.8 Backup Information",
            "1.9 Firewall log and storage setup",
            "1.10 Firewall License and Contract",
            "2.1 CPU",
            "2.2 Disk Utilization",
            "2.3 Network performance",
            "2.3 Interface Performance Statistics",
            "2.4 Interface Performance Statistics",
            "3.0 Firewall Rule Information",
            "4.0 Recommendation",
        ]

        found_headings = []
        for p_idx, page in enumerate(doc):
            if p_idx == 1:  # skip TOC
                continue
            for hp in heading_patterns:
                rects = page.search_for(hp)
                if rects:
                    found_headings.append({
                        "pattern": hp,
                        "page": p_idx,
                        "y": rects[0].y0,
                    })

        # Sort headings in page & vertical order
        found_headings.sort(key=lambda h: (h["page"], h["y"]))

        # For each heading, determine its content bounding box(es)
        section_crops: Dict[str, List[Path]] = {}

        for i, h in enumerate(found_headings):
            pat = h["pattern"]
            start_p = h["page"]
            start_y = max(65.0, h["y"] - 5.0)

            # Determine end position
            if i + 1 < len(found_headings):
                next_h = found_headings[i + 1]
                end_p = next_h["page"]
                end_y = next_h["y"] - 5.0
            else:
                end_p = start_p
                end_y = 780.0

            # Generate crops across pages
            images = self._crop_span(doc, start_p, start_y, end_p, end_y, output_dir, pat)
            section_crops[pat] = images

        # Build Appendix Mappings
        appendix_images: List[CheckPointAppendixImage] = []

        # Appendix 1: Version Checking (1.1 + 1.2)
        app1_crops = section_crops.get("1.1 System Information", []) + section_crops.get("1.2 Hardware Information", [])
        for img in app1_crops:
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=1,
                appendix_title="Appendix 1 – Version Checking",
                image_path=str(img),
                section_tag="version_checking",
                page_number=1,
            ))

        # Appendix 2: Interfaces (1.4)
        for img in section_crops.get("1.4 Interface information", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=2,
                appendix_title="Appendix 2 – Interfaces",
                image_path=str(img),
                section_tag="interfaces",
                page_number=2,
            ))

        # Appendix 3: Routing Information (1.5)
        for img in section_crops.get("1.5 Routing information", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=3,
                appendix_title="Appendix 3 – Routing Information",
                image_path=str(img),
                section_tag="routing",
                page_number=3,
            ))

        # Appendix 4: Power Supply & Hardware Sensors (1.3)
        for img in section_crops.get("1.3 Hardware Sensors", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=4,
                appendix_title="Appendix 4 – Power Supply & Hardware Sensors",
                image_path=str(img),
                section_tag="sensors",
                page_number=4,
            ))

        # Appendix 5: DNS Information (1.6)
        for img in section_crops.get("1.6 Domain Name Service Information", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=5,
                appendix_title="Appendix 5 – DNS Information",
                image_path=str(img),
                section_tag="dns",
                page_number=5,
            ))

        # Appendix 6: Date and Time (1.7)
        for img in section_crops.get("1.7 Firewall System Date and Time", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=6,
                appendix_title="Appendix 6 – Date and Time",
                image_path=str(img),
                section_tag="date_time",
                page_number=6,
            ))

        # Appendix 7: CPU Utilization (2.1)
        for img in section_crops.get("2.1 CPU", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=7,
                appendix_title="Appendix 7 – CPU Utilization",
                image_path=str(img),
                section_tag="cpu",
                page_number=7,
            ))

        # Appendix 8: Disk Usage (2.2)
        for img in section_crops.get("2.2 Disk Utilization", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=8,
                appendix_title="Appendix 8 – Disk Usage",
                image_path=str(img),
                section_tag="disk",
                page_number=8,
            ))

        # Appendix 9: Log Storage (1.9)
        for img in section_crops.get("1.9 Firewall log and storage setup", []):
            appendix_images.append(CheckPointAppendixImage(
                appendix_no=9,
                appendix_title="Appendix 9 – Log Storage",
                image_path=str(img),
                section_tag="log_storage",
                page_number=9,
            ))

        if is_gw:
            # Appendix 10: Network Performance (2.3)
            for img in section_crops.get("2.3 Network performance", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=10,
                    appendix_title="Appendix 10 – Network Performance",
                    image_path=str(img),
                    section_tag="network_perf",
                    page_number=10,
                ))

            # Appendix 11: Interface Performance Statistics (2.4)
            for img in section_crops.get("2.4 Interface Performance Statistics", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=11,
                    appendix_title="Appendix 11 – Interface Performance Statistics",
                    image_path=str(img),
                    section_tag="iface_stats",
                    page_number=11,
                ))

            # Appendix 12: License Status (1.10)
            for img in section_crops.get("1.10 Firewall License and Contract", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=12,
                    appendix_title="Appendix 12 – License Status",
                    image_path=str(img),
                    section_tag="license",
                    page_number=12,
                ))

            # Appendix 13: Backup Configuration (1.8)
            for img in section_crops.get("1.8 Backup Information", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=13,
                    appendix_title="Appendix 13 – Backup Configuration",
                    image_path=str(img),
                    section_tag="backup",
                    page_number=13,
                ))
        else:
            # Management Firewalls (12 appendices)
            # Appendix 10: Interface Performance Statistics (2.3)
            for img in section_crops.get("2.3 Interface Performance Statistics", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=10,
                    appendix_title="Appendix 10 – Interface Performance Statistics",
                    image_path=str(img),
                    section_tag="iface_stats",
                    page_number=10,
                ))

            # Appendix 11: License Status (1.10)
            for img in section_crops.get("1.10 Firewall License and Contract", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=11,
                    appendix_title="Appendix 11 – License Status",
                    image_path=str(img),
                    section_tag="license",
                    page_number=11,
                ))

            # Appendix 12: Backup Configuration (1.8)
            for img in section_crops.get("1.8 Backup Information", []):
                appendix_images.append(CheckPointAppendixImage(
                    appendix_no=12,
                    appendix_title="Appendix 12 – Backup Configuration",
                    image_path=str(img),
                    section_tag="backup",
                    page_number=12,
                ))

        device.appendix_images = appendix_images

        # Recommendation Crop (4.0 Recommendation)
        rec_crops = section_crops.get("4.0 Recommendation", [])
        if rec_crops:
            device.recommendation_crop_path = str(rec_crops[0])

    def _crop_span(
        self,
        doc: pymupdf.Document,
        start_p: int,
        start_y: float,
        end_p: int,
        end_y: float,
        output_dir: Path,
        section_name: str
    ) -> List[Path]:
        saved_paths = []
        clean_tag = re.sub(r"[^a-zA-Z0-9]+", "_", section_name).strip("_")

        left = 50.0
        right = 545.0
        header_y = 65.0
        footer_y = 780.0

        for p_no in range(start_p, end_p + 1):
            page = doc[p_no]
            y0 = start_y if p_no == start_p else header_y
            y1 = end_y if p_no == end_p else footer_y

            if y1 - y0 < 15.0:
                continue

            # If the block is very tall (> 460 pt), split into two clean halves
            total_h = y1 - y0
            if total_h > 460.0:
                half_h = total_h / 2.0
                splits = [(y0, y0 + half_h), (y0 + half_h, y1)]
            else:
                splits = [(y0, y1)]

            for s_idx, (sy0, sy1) in enumerate(splits):
                clip_rect = pymupdf.Rect(left, sy0, right, sy1)
                pix = page.get_pixmap(clip=clip_rect, dpi=self.dpi)
                file_name = f"{clean_tag}_p{p_no+1}_{s_idx}.png"
                out_path = output_dir / file_name
                pix.save(str(out_path))
                saved_paths.append(out_path)

        return saved_paths
