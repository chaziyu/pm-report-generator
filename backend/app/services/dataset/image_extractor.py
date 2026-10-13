"""
Image extractor for PM Report Dataset Importer.
Extracts embedded media from DOCX zip archive, maps images semantically to
appendix sections using XML and relationship structures, and excludes logos/decorative images.
"""

import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from xml.etree import ElementTree as ET
from PIL import Image
import docx
from docx.oxml.ns import qn

from .dataset_manifest import ImageManifestEntry, AppendixManifestEntry

APPENDIX_INFO: Dict[int, Dict[str, str]] = {
    1: {"slug": "cpu", "title": "CPU Usage"},
    2: {"slug": "memory", "title": "Memory Usage"},
    3: {"slug": "interface", "title": "Interface"},
    4: {"slug": "license", "title": "License Info"},
    5: {"slug": "firmware", "title": "Firmware Version"},
    6: {"slug": "vpn", "title": "VPN Tunnels"},
    7: {"slug": "routing", "title": "Static Routes & Routing Table"},
    8: {"slug": "uptime", "title": "Firewall System Uptime"},
    9: {"slug": "gui", "title": "Accessed via GUI"},
    10: {"slug": "cli", "title": "Accessed via CLI/SSH"},
    11: {"slug": "signatures", "title": "Signatures Version"},
    12: {"slug": "datetime", "title": "Firewall Date & Time"},
    13: {"slug": "ha", "title": "HA Status"},
    14: {"slug": "event", "title": "System Event"},
    15: {"slug": "log_manager", "title": "Log Manager Setting"},
    16: {"slug": "backup", "title": "Backup Configuration"},
}

NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

def extract_images_and_appendices(
    docx_path: Path,
    output_images_dir: Path,
    output_appendices_dir: Path
) -> Tuple[List[ImageManifestEntry], Dict[str, AppendixManifestEntry], List[str]]:
    """
    Extracts all images from docx_path, classifies them, saves them into
    output_images_dir and output_appendices_dir, and builds manifest entries.
    """
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_appendices_dir.mkdir(parents=True, exist_ok=True)

    warnings: List[str] = []
    image_entries: List[ImageManifestEntry] = []
    appendix_entries: Dict[str, AppendixManifestEntry] = {}

    # Initialize empty appendix entries
    for num, info in APPENDIX_INFO.items():
        appendix_entries[str(num)] = AppendixManifestEntry(
            appendix=num,
            title=info["title"],
            images=[],
            mapping_confidence=1.0
        )

    # 1. Read ZIP package relationships and media parts
    doc_rels: Dict[str, str] = {}
    header_footer_targets: set = set()
    media_blobs: Dict[str, bytes] = {}

    with zipfile.ZipFile(docx_path, "r") as z:
        for name in z.namelist():
            if name.startswith("word/media/"):
                media_blobs[name] = z.read(name)
            elif name.startswith("word/_rels/header") or name.startswith("word/_rels/footer"):
                try:
                    hroot = ET.fromstring(z.read(name))
                    for r in hroot:
                        if "image" in r.attrib.get("Type", ""):
                            header_footer_targets.add(r.attrib.get("Target", ""))
                except Exception:
                    pass
            elif name == "word/_rels/document.xml.rels":
                try:
                    droot = ET.fromstring(z.read(name))
                    for r in droot:
                        if "image" in r.attrib.get("Type", ""):
                            doc_rels[r.attrib["Id"]] = r.attrib.get("Target", "")
                except Exception:
                    pass

    # Normalize media paths in targets
    def normalize_target(t: str) -> str:
        t = t.replace("\\", "/")
        if not t.startswith("word/"):
            if t.startswith("media/"):
                return f"word/{t}"
            return f"word/{t.lstrip('/')}"
        return t

    target_to_rids: Dict[str, List[str]] = {}
    rid_to_target: Dict[str, str] = {}
    for rid, tgt in doc_rels.items():
        norm = normalize_target(tgt)
        rid_to_target[rid] = norm
        target_to_rids.setdefault(norm, []).append(rid)

    # Load document using python-docx to inspect layout
    doc = docx.Document(docx_path)

    # 2. Identify decorative images (headers/footers, cover page, signatures)
    classified_rids: Dict[str, Dict[str, Any]] = {}

    # A. Header / Footer targets
    for hf_tgt in header_footer_targets:
        norm = normalize_target(hf_tgt)
        for rid in target_to_rids.get(norm, []):
            classified_rids[rid] = {
                "classified_as": "decorative",
                "reason": "header_footer_image"
            }

    # B. Cover paragraphs (paragraphs before the first table)
    # Scan document body paragraphs outside tables
    first_table_seen = False
    for p in doc.paragraphs:
        # Check if this paragraph contains blips
        blips = p._p.xpath(".//a:blip")
        for b in blips:
            rid = b.get(qn("r:embed"))
            if rid and rid not in classified_rids:
                # Cover page or body figure
                classified_rids[rid] = {
                    "classified_as": "decorative",
                    "reason": "cover_page_logo"
                }

    # C. Table 0 (Author Details) signature image
    if len(doc.tables) > 0:
        t0 = doc.tables[0]
        # Look for signature cell in Author's details table
        for r_idx, row in enumerate(t0.rows):
            for c_idx, cell in enumerate(row.cells):
                blips = cell._tc.xpath(".//a:blip")
                for b in blips:
                    rid = b.get(qn("r:embed"))
                    if rid and rid not in classified_rids:
                        classified_rids[rid] = {
                            "classified_as": "signature",
                            "reason": "author_signature"
                        }

    # D. Table 3 (Key Highlight) or other non-appendix body tables before Table 4
    for t_idx, t in enumerate(doc.tables[:4]):
        for r_idx, row in enumerate(t.rows):
            for c_idx, cell in enumerate(row.cells):
                cell_text = cell.text.lower()
                if "appendix" not in cell_text:
                    blips = cell._tc.xpath(".//a:blip")
                    for b in blips:
                        rid = b.get(qn("r:embed"))
                        if rid and rid not in classified_rids:
                            classified_rids[rid] = {
                                "classified_as": "decorative",
                                "reason": "body_figure"
                            }

    # 3. Map appendix images
    # We examine tables that contain appendix captions
    appendix_image_rids: Dict[int, List[str]] = {num: [] for num in range(1, 17)}
    caption_regex = re.compile(r"(?i)\bappendix\s*(\d+)[\s:\-–—\.]*(.*)")

    for t_idx, t in enumerate(doc.tables):
        # Quick check if table might contain appendix content
        table_text = " ".join(c.text.lower() for row in t.rows for c in row.cells)
        if "appendix" not in table_text:
            continue

        for r_idx, row in enumerate(t.rows):
            for c_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                # Skip checklist reference cells like "Refer Appendix 1"
                if "refer appendix" in cell_text.lower():
                    continue

                unassigned_images: List[str] = []
                current_cap: Optional[int] = None

                for p in cell.paragraphs:
                    blips = p._p.xpath(".//a:blip")
                    raw_rids = [b.get(qn("r:embed")) for b in blips if b.get(qn("r:embed"))]
                    # Filter out already classified decorative / signature images
                    rids = [
                        r for r in raw_rids
                        if classified_rids.get(r, {}).get("classified_as") not in ("decorative", "signature", "body_figure")
                    ]
                    p_text = p.text.strip()
                    m = caption_regex.search(p_text)

                    if m:
                        num = int(m.group(1))
                        raw_title = m.group(2).strip()
                        if 1 <= num <= 16:
                            if unassigned_images:
                                # Pattern A: Images came before the caption
                                appendix_image_rids[num].extend(unassigned_images)
                                if raw_title:
                                    appendix_entries[str(num)].title = raw_title
                                unassigned_images = []
                                current_cap = None
                            else:
                                # Pattern B: Caption comes before images
                                current_cap = num
                                if raw_title:
                                    appendix_entries[str(num)].title = raw_title
                    elif rids:
                        if current_cap is not None:
                            appendix_image_rids[current_cap].extend(rids)
                        else:
                            unassigned_images.extend(rids)

                # If there are still unassigned images in a cell that had a caption
                if unassigned_images and current_cap is not None:
                    appendix_image_rids[current_cap].extend(unassigned_images)
                elif unassigned_images:
                    # Ambiguous images without caption
                    for rid in unassigned_images:
                        warnings.append(
                            f"Image {rid} in Table {t_idx} Row {r_idx} could not be unambiguously mapped to an appendix caption"
                        )
                        if rid not in classified_rids:
                            classified_rids[rid] = {
                                "classified_as": "other",
                                "reason": "unassigned_in_appendix_table"
                            }

    # Mark appendix classified images
    for num, rids in appendix_image_rids.items():
        for rid in rids:
            classified_rids[rid] = {
                "classified_as": "appendix",
                "appendix_number": num,
                "reason": f"mapped_to_appendix_{num}"
            }

    # 4. Extract and save images
    extracted_image_map: Dict[str, str] = {}  # norm_target -> saved_filename in images/
    img_counter = 1

    # Extract all media parts found
    for norm_target, blob in sorted(media_blobs.items()):
        ext_filename = f"extracted_image_{img_counter:03d}.png"
        saved_img_path = output_images_dir / ext_filename
        
        # Read image dimensions
        width = None
        height = None
        try:
            with Image.open(io.BytesIO(blob)) as img:
                width, height = img.size
                # Save normalized PNG
                img.save(saved_img_path, format="PNG")
        except Exception:
            # Fallback to direct bytes write if PIL fails
            saved_img_path.write_bytes(blob)

        extracted_image_map[norm_target] = ext_filename
        img_counter += 1

    # 5. Populate ImageManifestEntry list
    for norm_target, saved_filename in extracted_image_map.items():
        rids = target_to_rids.get(norm_target, ["unknown_rId"])
        # Use first rid or most relevant
        primary_rid = rids[0]
        classification = classified_rids.get(primary_rid, {
            "classified_as": "decorative" if any(hf in norm_target for hf in header_footer_targets) else "other",
            "reason": "unmatched_media_part"
        })

        # Read dimensions from saved PNG
        saved_path = output_images_dir / saved_filename
        w, h = None, None
        try:
            with Image.open(saved_path) as im:
                w, h = im.size
        except Exception:
            pass

        entry = ImageManifestEntry(
            source_part=norm_target,
            relationship_id=primary_rid,
            width=w,
            height=h,
            classified_as=classification.get("classified_as", "other"),
            appendix_number=classification.get("appendix_number"),
            saved_name=saved_filename,
            reason=classification.get("reason")
        )
        image_entries.append(entry)

    # 6. Save mapped appendix screenshots into appendices/
    for num in range(1, 17):
        rids = appendix_image_rids.get(num, [])
        slug = APPENDIX_INFO[num]["slug"]
        saved_appendix_filenames: List[str] = []

        if not rids:
            warnings.append(f"Appendix {num} ({APPENDIX_INFO[num]['title']}) has no associated images found")
            appendix_entries[str(num)].mapping_confidence = 0.0
            continue

        for idx, rid in enumerate(rids):
            target = rid_to_target.get(rid)
            blob = media_blobs.get(target) if target else None

            if not blob:
                warnings.append(f"Appendix {num} image {rid} blob could not be found in media parts")
                continue

            if len(rids) == 1:
                app_filename = f"appendix_{num:02d}_{slug}.png"
            else:
                app_filename = f"appendix_{num:02d}_{idx + 1:02d}.png"

            dest_path = output_appendices_dir / app_filename
            try:
                with Image.open(io.BytesIO(blob)) as im:
                    im.save(dest_path, format="PNG")
            except Exception:
                dest_path.write_bytes(blob)

            saved_appendix_filenames.append(app_filename)

        appendix_entries[str(num)].images = saved_appendix_filenames

    return image_entries, appendix_entries, warnings
