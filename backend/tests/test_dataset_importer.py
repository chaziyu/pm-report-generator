"""
Tests for PM Report Dataset Importer.
Uses synthetic DOCX fixtures to ensure no sensitive/customer data is committed.
"""

import hashlib
import io
import json
import shutil
import tempfile
import unittest
import sys
from pathlib import Path
from PIL import Image
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.dataset.report_importer import (
    ReportImporter,
    calculate_sha256,
    is_supported_fortigate_pm
)
from app.services.dataset.image_extractor import (
    extract_images_and_appendices,
    APPENDIX_INFO
)
from app.services.dataset.expected_value_extractor import (
    extract_expected_values,
    get_cell_checkbox_status
)

CHECKED_GLYPH = "\u2612"    # ☒
UNCHECKED_GLYPH = "\u2610"  # ☐
W14_VAL = "{http://schemas.microsoft.com/office/word/2010/wordml}val"

def create_solid_image_bytes(color: str = "blue", size: tuple = (100, 100)) -> bytes:
    """Creates a simple solid-color PNG image in bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()

def add_sdt_checkbox(cell, option_text: str, is_checked: bool):
    """Adds a Word Structured Document Tag (SDT) checkbox to a cell paragraph."""
    p = cell.add_paragraph()
    p_elm = p._p

    sdt = OxmlElement("w:sdt")
    sdtPr = OxmlElement("w:sdtPr")
    chk = OxmlElement("w14:checkbox")
    checked_el = OxmlElement("w14:checked")
    checked_el.set(qn("w14:val"), "1" if is_checked else "0")
    chk.append(checked_el)
    sdtPr.append(chk)
    sdt.append(sdtPr)

    sdtContent = OxmlElement("w:sdtContent")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = (CHECKED_GLYPH if is_checked else UNCHECKED_GLYPH) + f" {option_text}"
    r.append(t)
    sdtContent.append(r)
    sdt.append(sdtContent)

    p_elm.append(sdt)

def build_synthetic_pm_docx(dest_path: Path, include_logo: bool = True, num_app7_images: int = 2) -> Path:
    """
    Builds a synthetic FortiGate PM report DOCX with:
    - Cover textboxes (customer, PM Date, FSMS, contract)
    - Optional header logo
    - Table 0 (Author Details) with signature image
    - Table 2 (Application Info)
    - Table 4 (Hardware) with checkboxes
    - Table 5 (Licensing)
    - Table 6 (Firmware)
    - Table 7 (VPN)
    - Table 9 (Configuration)
    - Appendix tables with synthetic screenshots
    """
    doc = docx.Document()

    # 1. Add Cover page header / logo
    if include_logo:
        logo_bytes = create_solid_image_bytes("red", (200, 50))
        logo_stream = io.BytesIO(logo_bytes)
        p_logo = doc.add_paragraph()
        p_logo.add_run().add_picture(logo_stream, width=docx.shared.Inches(2))

    # Add cover paragraphs
    doc.add_paragraph("Customer: Synthetic Customer Ltd")
    doc.add_paragraph("PM DATE: 15/09/2026")
    doc.add_paragraph("FSMS ID: 99887766")
    doc.add_paragraph("CONTRACT NO: SYN/2026/001")
    doc.add_paragraph("CONTRACT PERIOD: 01/01/2026 - 31/12/2026")

    # Table 0: Author Details
    t0 = doc.add_table(rows=5, cols=3)
    t0.rows[0].cells[0].text = "Author's Details"
    t0.rows[1].cells[0].text = "Name"
    t0.rows[1].cells[2].text = "Test Engineer"
    t0.rows[2].cells[0].text = "Date"
    t0.rows[2].cells[2].text = "15/09/2026"
    t0.rows[4].cells[0].text = "Signature"
    sig_stream = io.BytesIO(create_solid_image_bytes("black", (80, 40)))
    t0.rows[4].cells[2].paragraphs[0].add_run().add_picture(sig_stream)

    # Table 1: Survey
    doc.add_table(rows=2, cols=2)

    # Table 2: Application Info
    t2 = doc.add_table(rows=3, cols=2)
    t2.rows[0].cells[0].text = "Model"
    t2.rows[0].cells[1].text = "FortiGate 200F"
    t2.rows[1].cells[0].text = "Hostname"
    t2.rows[1].cells[1].text = "SYN_FG200F_CLUSTER"
    t2.rows[2].cells[0].text = "Serial Number"
    t2.rows[2].cells[1].text = "FG200FT12345678 (Primary), FG200FT87654321 (Secondary)"

    # Table 3: Key Highlight
    doc.add_table(rows=2, cols=1)

    # Table 4: Hardware Health Check
    t4 = doc.add_table(rows=5, cols=5)
    for r in t4.rows:
        r.cells[0].text = "1.x"
    t4.rows[1].cells[0].text = "1.1"
    t4.rows[1].cells[1].text = "Hard disk space (If any)"
    add_sdt_checkbox(t4.rows[1].cells[3], "Healthy", False)
    add_sdt_checkbox(t4.rows[1].cells[3], "Unhealthy", False)
    add_sdt_checkbox(t4.rows[1].cells[3], "N/A", True)

    t4.rows[2].cells[0].text = "1.2"
    t4.rows[2].cells[1].text = "CPU Usage"
    add_sdt_checkbox(t4.rows[2].cells[3], "Healthy", True)
    add_sdt_checkbox(t4.rows[2].cells[3], "Unhealthy", False)
    add_sdt_checkbox(t4.rows[2].cells[3], "N/A", False)
    t4.rows[2].cells[4].text = "CPU usage: 12%\nRefer Appendix 1"

    t4.rows[3].cells[0].text = "1.3"
    t4.rows[3].cells[1].text = "Memory Usage"
    add_sdt_checkbox(t4.rows[3].cells[3], "Healthy", True)
    add_sdt_checkbox(t4.rows[3].cells[3], "Unhealthy", False)
    add_sdt_checkbox(t4.rows[3].cells[3], "N/A", False)
    t4.rows[3].cells[4].text = "Memory usage: 45%\nRefer Appendix 2"

    t4.rows[4].cells[0].text = "1.4"
    t4.rows[4].cells[1].text = "Interface Monitoring"
    add_sdt_checkbox(t4.rows[4].cells[3], "Healthy", True)
    t4.rows[4].cells[4].text = "Ports in-used: 8\nRefer Appendix 3"

    # Table 5: Licensing
    t5 = doc.add_table(rows=3, cols=5)
    t5.rows[1].cells[0].text = "2.1"
    t5.rows[1].cells[1].text = "FortiCare Support"
    add_sdt_checkbox(t5.rows[1].cells[3], "Valid", True)
    t5.rows[1].cells[4].text = "Expiration Date: 20/10/2027\nRefer Appendix 4"

    t5.rows[2].cells[0].text = "2.2"
    t5.rows[2].cells[1].text = "UTM Bundle Update: Antivirus IPS Web Filtering Anti-Spam Others"
    add_sdt_checkbox(t5.rows[2].cells[3], "Valid", True)

    # Table 6: Firmware
    t6 = doc.add_table(rows=4, cols=5)
    t6.rows[1].cells[0].text = "3.1"
    t6.rows[1].cells[1].text = "Firewall Firmware Version"
    add_sdt_checkbox(t6.rows[1].cells[3], "Out-of-Date", True)
    t6.rows[1].cells[4].text = "Current Firmware Version: v7.4.11 build2878 (Mature)\nLatest Firmware Version: v7.4.12"

    t6.rows[2].cells[0].text = "3.2"
    t6.rows[2].cells[1].text = "Final Firmware Release (FFR)"
    add_sdt_checkbox(t6.rows[2].cells[3], "N/A", True)

    t6.rows[3].cells[0].text = "3.3"
    t6.rows[3].cells[1].text = "End of Support Date (EOS)"
    add_sdt_checkbox(t6.rows[3].cells[3], "Valid", True)

    # Table 7: VPN
    t7 = doc.add_table(rows=2, cols=5)
    t7.rows[1].cells[0].text = "4.1"
    t7.rows[1].cells[1].text = "Check Number Of tunnel"
    t7.rows[1].cells[3].text = "Total VPN Tunnel(s): 5\nActive VPN Tunnel(s): 4\nInactive VPN Tunnel(s): 1"

    # Table 8: Routing
    t8 = doc.add_table(rows=2, cols=5)
    t8.rows[1].cells[0].text = "5.1"
    t8.rows[1].cells[1].text = "Firewall Routing Table"
    t8.rows[1].cells[3].text = "Static route and routing monitor information"

    # Table 9: Configuration
    t9 = doc.add_table(rows=11, cols=5)
    t9.rows[1].cells[0].text = "6.1"
    t9.rows[1].cells[1].text = "Firewall System Uptime"
    t9.rows[1].cells[3].text = "Uptime: 20 day(s) 5 hour(s) 10 min(s)"

    t9.rows[2].cells[0].text = "6.2"
    t9.rows[2].cells[1].text = "Accessibility of FortiGate via GUI"
    add_sdt_checkbox(t9.rows[2].cells[3], "Pass", True)

    t9.rows[3].cells[0].text = "6.3"
    t9.rows[3].cells[1].text = "Accessibility of FortiGate via CLI"
    add_sdt_checkbox(t9.rows[3].cells[3], "Pass", True)

    t9.rows[4].cells[0].text = "6.4"
    t9.rows[4].cells[1].text = "Signatures version"
    add_sdt_checkbox(t9.rows[4].cells[3], "Up-to-Date", True)

    t9.rows[5].cells[0].text = "6.5"
    t9.rows[5].cells[1].text = "Firewall Date & Time"
    add_sdt_checkbox(t9.rows[5].cells[3], "Pass", True)
    t9.rows[5].cells[4].text = "Time zone is set as GMT +8"

    t9.rows[6].cells[0].text = "6.6"
    t9.rows[6].cells[1].text = "Firewall Internet Access"
    add_sdt_checkbox(t9.rows[6].cells[3], "Pass", True)

    t9.rows[7].cells[0].text = "6.7"
    t9.rows[7].cells[1].text = "High Availability (if any)"
    add_sdt_checkbox(t9.rows[7].cells[3], "Pass", True)

    t9.rows[8].cells[0].text = "6.8"
    t9.rows[8].cells[1].text = "Logging (Event Log)"
    add_sdt_checkbox(t9.rows[8].cells[3], "Available", True)

    t9.rows[9].cells[0].text = "6.9"
    t9.rows[9].cells[1].text = "Log Manager (if any)"
    add_sdt_checkbox(t9.rows[9].cells[3], "Healthy", True)

    t9.rows[10].cells[0].text = "6.10"
    t9.rows[10].cells[1].text = "Backup Configurations"
    add_sdt_checkbox(t9.rows[10].cells[3], "Passed", True)

    # 10. Add Appendix Table
    # Appendix 1: CPU Usage (1 image)
    t_app = doc.add_table(rows=16, cols=1)
    
    # App 1
    cell1 = t_app.rows[0].cells[0]
    p_img1 = cell1.add_paragraph()
    p_img1.add_run().add_picture(io.BytesIO(create_solid_image_bytes("green", (300, 150))))
    cell1.add_paragraph("Appendix 1 - CPU Usage")

    # App 2
    cell2 = t_app.rows[1].cells[0]
    p_img2 = cell2.add_paragraph()
    p_img2.add_run().add_picture(io.BytesIO(create_solid_image_bytes("yellow", (300, 150))))
    cell2.add_paragraph("Appendix 2 - Memory Usage")

    # App 3 to 6
    for app_idx in range(3, 7):
        c = t_app.rows[app_idx - 1].cells[0]
        p = c.add_paragraph()
        p.add_run().add_picture(io.BytesIO(create_solid_image_bytes("purple", (300, 150))))
        c.add_paragraph(f"Appendix {app_idx} - {APPENDIX_INFO[app_idx]['title']}")

    # App 7: Multiple images (e.g. 2 images)
    cell7 = t_app.rows[6].cells[0]
    for img_i in range(num_app7_images):
        p_img = cell7.add_paragraph()
        p_img.add_run().add_picture(io.BytesIO(create_solid_image_bytes("cyan", (300, 150))))
    cell7.add_paragraph("Appendix 7 - Static Routes & Routing Table")

    # App 8 to 16
    for app_idx in range(8, 17):
        c = t_app.rows[app_idx - 1].cells[0]
        p = c.add_paragraph()
        p.add_run().add_picture(io.BytesIO(create_solid_image_bytes("orange", (300, 150))))
        c.add_paragraph(f"Appendix {app_idx} - {APPENDIX_INFO[app_idx]['title']}")

    doc.save(dest_path)
    return dest_path


class TestPMReportDatasetImporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pm_test_"))
        self.dataset_dir = self.temp_dir / "dataset"
        self.fixtures_dir = self.temp_dir / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_media_from_docx(self):
        """Tests that embedded images are extracted from DOCX and dimensions are read."""
        doc_path = self.fixtures_dir / "report_extract.docx"
        build_synthetic_pm_docx(doc_path)

        images_dir = self.temp_dir / "extracted_images"
        appendices_dir = self.temp_dir / "appendices"

        image_entries, appendix_entries, warnings = extract_images_and_appendices(
            docx_path=doc_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        self.assertGreater(len(image_entries), 0)
        # Check that PNG files exist in output_images_dir
        saved_files = list(images_dir.glob("*.png"))
        self.assertEqual(len(saved_files), len(image_entries))
        # Ensure dimensions were read
        for entry in image_entries:
            self.assertIsNotNone(entry.width)
            self.assertIsNotNone(entry.height)

    def test_exclude_logos(self):
        """Tests that cover logos and author signatures are classified as decorative/signature and not as appendix screenshots."""
        doc_path = self.fixtures_dir / "report_logos.docx"
        build_synthetic_pm_docx(doc_path, include_logo=True)

        images_dir = self.temp_dir / "images"
        appendices_dir = self.temp_dir / "appendices"

        image_entries, appendix_entries, warnings = extract_images_and_appendices(
            docx_path=doc_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        classifications = {e.classified_as for e in image_entries}
        self.assertIn("decorative", classifications)
        self.assertIn("signature", classifications)
        self.assertIn("appendix", classifications)

        # Ensure decorative images are not assigned to any appendix
        for entry in image_entries:
            if entry.classified_as in ("decorative", "signature"):
                self.assertIsNone(entry.appendix_number)

    def test_mapping_image_to_appendix_caption(self):
        """Tests that an image is correctly mapped to its nearest appendix caption."""
        doc_path = self.fixtures_dir / "report_map.docx"
        build_synthetic_pm_docx(doc_path)

        images_dir = self.temp_dir / "images"
        appendices_dir = self.temp_dir / "appendices"

        image_entries, appendix_entries, warnings = extract_images_and_appendices(
            docx_path=doc_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        # Appendix 1 should have exactly 1 image
        app1 = appendix_entries.get("1")
        self.assertIsNotNone(app1)
        self.assertEqual(len(app1.images), 1)
        self.assertEqual(app1.images[0], "appendix_01_cpu.png")
        self.assertTrue((appendices_dir / "appendix_01_cpu.png").exists())

    def test_multiple_images_per_appendix(self):
        """Tests that appendices with multiple screenshots preserve all images and ordering."""
        doc_path = self.fixtures_dir / "report_multi.docx"
        build_synthetic_pm_docx(doc_path, num_app7_images=3)

        images_dir = self.temp_dir / "images"
        appendices_dir = self.temp_dir / "appendices"

        image_entries, appendix_entries, warnings = extract_images_and_appendices(
            docx_path=doc_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        app7 = appendix_entries.get("7")
        self.assertIsNotNone(app7)
        self.assertEqual(len(app7.images), 3)
        self.assertEqual(app7.images, ["appendix_07_01.png", "appendix_07_02.png", "appendix_07_03.png"])
        for img_name in app7.images:
            self.assertTrue((appendices_dir / img_name).exists())

    def test_extract_pm_body_values(self):
        """Tests extraction of ground-truth values from report body."""
        doc_path = self.fixtures_dir / "report_values.docx"
        build_synthetic_pm_docx(doc_path)
        doc = docx.Document(doc_path)

        expected, warnings = extract_expected_values(doc)

        self.assertEqual(expected["metadata"]["customer"], "Synthetic Customer Ltd")
        self.assertEqual(expected["metadata"]["pm_date"], "15/09/2026")
        self.assertEqual(expected["metadata"]["fsms_id"], "99887766")
        self.assertEqual(expected["metadata"]["contract_number"], "SYN/2026/001")
        self.assertEqual(expected["application"]["model"], "FortiGate 200F")
        self.assertEqual(expected["application"]["hostname"], "SYN_FG200F_CLUSTER")
        self.assertEqual(expected["application"]["serial_primary"], "FG200FT12345678")
        self.assertEqual(expected["application"]["serial_secondary"], "FG200FT87654321")
        self.assertEqual(expected["hardware"]["cpu_usage"], 12)
        self.assertEqual(expected["hardware"]["cpu_status"], "healthy")
        self.assertEqual(expected["hardware"]["memory_usage"], 45)
        self.assertEqual(expected["hardware"]["active_ports"], 8)
        self.assertEqual(expected["licensing"]["forticare_status"], "valid")
        self.assertEqual(expected["licensing"]["expiration_date"], "20/10/2027")
        self.assertEqual(expected["firmware"]["current"], "7.4.11")
        self.assertEqual(expected["firmware"]["build"], "2878")
        self.assertEqual(expected["firmware"]["maturity"], "Mature")
        self.assertEqual(expected["firmware"]["recommended"], "7.4.12")
        self.assertEqual(expected["firmware"]["status"], "out_of_date")
        self.assertEqual(expected["vpn"]["total"], 5)
        self.assertEqual(expected["vpn"]["active"], 4)
        self.assertEqual(expected["vpn"]["inactive"], 1)
        self.assertEqual(expected["configuration"]["timezone"], "GMT +8")
        self.assertEqual(expected["configuration"]["uptime"], "20 day(s) 5 hour(s) 10 min(s)")

    def test_reading_checkbox_states(self):
        """Tests reading checkbox states from cells."""
        doc = docx.Document()
        tbl = doc.add_table(rows=1, cols=1)
        cell = tbl.rows[0].cells[0]
        add_sdt_checkbox(cell, "Healthy", True)
        add_sdt_checkbox(cell, "Unhealthy", False)
        add_sdt_checkbox(cell, "N/A", False)

        status = get_cell_checkbox_status(cell, ["Healthy", "Unhealthy", "N/A"])
        self.assertEqual(status, "healthy")

    def test_unresolved_appendix_handling(self):
        """Tests that missing appendix screenshots are marked as unresolved with warnings."""
        doc = docx.Document()
        doc.add_paragraph("Model: FortiGate 100E")
        # Empty appendix table with caption but no image
        t_app = doc.add_table(rows=1, cols=1)
        t_app.rows[0].cells[0].add_paragraph("Appendix 1 - CPU Usage")
        doc_path = self.fixtures_dir / "unresolved_app.docx"
        doc.save(doc_path)

        images_dir = self.temp_dir / "images"
        appendices_dir = self.temp_dir / "appendices"

        image_entries, appendix_entries, warnings = extract_images_and_appendices(
            docx_path=doc_path,
            output_images_dir=images_dir,
            output_appendices_dir=appendices_dir
        )

        app1 = appendix_entries.get("1")
        self.assertIsNotNone(app1)
        self.assertEqual(len(app1.images), 0)
        self.assertEqual(app1.mapping_confidence, 0.0)
        self.assertTrue(any("no associated images" in w for w in warnings))

    def test_duplicate_report_detection(self):
        """Tests duplicate report detection and skipping."""
        doc_path = self.fixtures_dir / "report_dup.docx"
        build_synthetic_pm_docx(doc_path)

        importer = ReportImporter(output_dir=self.dataset_dir, overwrite=False)

        # First import -> succeeds
        res1 = importer.import_single_report(doc_path)
        self.assertEqual(res1["status"], "imported")

        # Second import -> detected as duplicate
        res2 = importer.import_single_report(doc_path)
        self.assertEqual(res2["status"], "duplicate")
        self.assertIn("Duplicate report already imported", res2["message"])

        # With overwrite -> re-imports
        importer_overwrite = ReportImporter(output_dir=self.dataset_dir, overwrite=True)
        res3 = importer_overwrite.import_single_report(doc_path)
        self.assertEqual(res3["status"], "imported")

    def test_source_report_immutability(self):
        """Tests that the importer never alters the source report."""
        doc_path = self.fixtures_dir / "report_immutable.docx"
        build_synthetic_pm_docx(doc_path)

        sha_before = calculate_sha256(doc_path)

        importer = ReportImporter(output_dir=self.dataset_dir)
        res = importer.import_single_report(doc_path)
        self.assertEqual(res["status"], "imported")

        sha_after = calculate_sha256(doc_path)
        self.assertEqual(sha_before, sha_after, "Source report SHA-256 changed after import!")

    def test_batch_import_continues_after_bad_report(self):
        """Tests that batch import handles a bad or unsupported file and continues processing."""
        # 1. Valid report
        valid_path = self.fixtures_dir / "valid_report.docx"
        build_synthetic_pm_docx(valid_path)

        # 2. Corrupt / invalid docx
        bad_path = self.fixtures_dir / "bad_report.docx"
        bad_path.write_bytes(b"NOT_A_VALID_DOCX_FILE_DATA")

        # 3. Unsupported variant
        unsupported_doc = docx.Document()
        t = unsupported_doc.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "Model"
        t.rows[0].cells[1].text = "Check Point 7000"
        unsupported_path = self.fixtures_dir / "checkpoint.docx"
        unsupported_doc.save(unsupported_path)

        importer = ReportImporter(output_dir=self.dataset_dir)
        summary, results = importer.import_batch(self.fixtures_dir)

        self.assertEqual(summary.reports_scanned, 3)
        self.assertEqual(summary.reports_imported, 1)
        self.assertEqual(summary.reports_failed, 1)
        self.assertEqual(summary.unsupported_template_variants, 1)


if __name__ == "__main__":
    unittest.main()
