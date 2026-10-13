#!/usr/bin/env python3
"""
CLI Tool: CheckPoint Vendor PM to CTC Format Converter
Ingests Vendor PM reports (PDF), extracts telemetry, evaluates health rules,
renders high-resolution appendix evidence, and generates the official CTC Word (.docx) report.
Also supports exporting supervised fine-tuning (SFT) / few-shot training dataset pairs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.checkpoint import (
    CheckpointVendorPMParser,
    CheckpointSectionCropper,
    CheckpointPMEvaluator,
    CheckpointCTCReportGenerator,
    CheckPointReportData,
    CheckPointDeviceData,
)

def export_training_dataset(
    devices: List[CheckPointDeviceData],
    output_jsonl: Path
) -> None:
    """
    Exports structured training dataset pairs for AI model fine-tuning and in-context learning.
    Each record contains prompt input (vendor PM telemetry) and expected target (CTC structured fields & checklist).
    """
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    records = []

    for dev in devices:
        # Prompt representation of vendor PM report text
        prompt_text = (
            f"VENDOR PREVENTIVE MAINTENANCE REPORT:\n"
            f"Device: {dev.system.hostname}\n"
            f"Model: {dev.system.model}\n"
            f"OS: {dev.system.os_version}\n"
            f"Check Point Version: {dev.system.cp_version}\n"
            f"Uptime: {dev.system.uptime}\n"
            f"Management IP: {dev.system.mgmt_ip}\n"
            f"RAM: {dev.hardware.ram}, Swap: {dev.hardware.swap}, CPU: {dev.hardware.cpu_specs}\n"
            f"Storage /var/log full: {dev.storage_log.var_log_full}, Max Disk: {dev.storage_log.max_disk_used_pct}%\n"
            f"Log Switch Enabled: {dev.storage_log.log_switch_enabled}\n"
            f"NTP Server: {dev.datetime_info.ntp_server_ip}, Backup: {dev.backup.backup_enabled}\n"
        )

        # Expected target representation
        target_data = {
            "device": dev.system.hostname,
            "executive_summary": {
                "model": dev.system.model,
                "serial": dev.system.serial,
                "mgmt_ip": dev.system.mgmt_ip,
                "date_pm": dev.system.date_pm,
                "highlights": dev.key_highlights,
                "recommendations": [r.dict() for r in dev.recommendations],
            },
            "checklist": [item.dict() for item in dev.checklist],
            "appendices_count": len(dev.appendix_images),
        }

        records.append({
            "prompt": prompt_text,
            "completion": json.dumps(target_data, indent=2)
        })

    with open(output_jsonl, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"Exported {len(records)} training samples to: {output_jsonl}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert CheckPoint Vendor PM reports (PDF) into official CTC Format DOCX report."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=str,
        help="Path to a vendor PM PDF file or directory containing PDF reports.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="workspace/output/CTC_CheckPoint_PM_Report.docx",
        help="Path for generated CTC Word report (.docx).",
    )
    parser.add_argument(
        "--template",
        "-t",
        type=str,
        default="doc/CIMB_3rd_Quater_of_2026_PM/CIMB_3rd_Quater_of_2026_Preventive_Maintenance_Report.docx",
        help="Path to base CTC template .docx file.",
    )
    parser.add_argument(
        "--customer",
        type=str,
        default="CIMB BANK BERHAD",
        help="Customer Name on cover page.",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="3rd Quarter Of 2026 Preventive Maintenance Report For Check Point Firewall",
        help="Report Title.",
    )
    parser.add_argument(
        "--author",
        type=str,
        default="Cha Zi Yu",
        help="Author Name.",
    )
    parser.add_argument(
        "--designation",
        type=str,
        default="Associate Technical Engineer",
        help="Author Designation.",
    )
    parser.add_argument(
        "--inventory",
        type=str,
        default=None,
        help="Path to JSON file with hostname->serial mapping or JSON string.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=str,
        default="workspace/checkpoint_pm/evidence",
        help="Directory to save rendered appendix evidence clips.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Render resolution DPI for appendix evidence crops (default: 150).",
    )
    parser.add_argument(
        "--export-training-dataset",
        type=str,
        default=None,
        help="Optional path to output supervised training dataset (.jsonl).",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path {input_path} does not exist.")
        sys.exit(1)

    # Collect PDF files
    if input_path.is_file():
        pdf_files = [input_path]
    else:
        pdf_files = sorted(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"Error: No PDF files found in {input_path}")
        sys.exit(1)

    # Load custom serial inventory if provided
    serial_inv = None
    if args.inventory:
        inv_p = Path(args.inventory)
        if inv_p.exists():
            with open(inv_p, "r", encoding="utf-8") as f:
                serial_inv = json.load(f)
        else:
            try:
                serial_inv = json.loads(args.inventory)
            except Exception:
                print(f"Warning: Could not parse inventory: {args.inventory}")

    parser_svc = CheckpointVendorPMParser(serial_inventory=serial_inv)
    cropper_svc = CheckpointSectionCropper(dpi=args.dpi)
    evaluator_svc = CheckpointPMEvaluator()
    generator_svc = CheckpointCTCReportGenerator()

    evidence_base = Path(args.evidence_dir)
    evidence_base.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(pdf_files)} vendor PM reports...")
    devices = []
    for pdf_f in pdf_files:
        print(f"  -> Parsing: {pdf_f.name}")
        dev = parser_svc.parse_pdf(pdf_f)
        evaluator_svc.evaluate(dev)

        dev_evidence_dir = evidence_base / dev.system.hostname
        print(f"  -> Cropping evidence to: {dev_evidence_dir}")
        cropper_svc.crop_device_evidence(pdf_f, dev, dev_evidence_dir)

        devices.append(dev)
        print(f"     [OK] {dev.system.hostname} ({dev.system.model}) - {len(dev.appendix_images)} evidence images")

    report_data = CheckPointReportData(
        customer=args.customer,
        report_title=args.title,
        author_name=args.author,
        author_designation=args.designation,
        devices=devices,
    )

    out_docx = Path(args.output)
    tmpl_docx = Path(args.template) if args.template else None

    print(f"Generating CTC format Word report: {out_docx}...")
    final_report = generator_svc.generate_report(
        report_data=report_data,
        output_path=out_docx,
        template_path=tmpl_docx,
    )
    print(f"[SUCCESS] Report successfully generated at: {final_report}")
    print(f"          Report size: {final_report.stat().st_size:,} bytes")

    if args.export_training_dataset:
        ds_path = Path(args.export_training_dataset)
        export_training_dataset(devices, ds_path)

if __name__ == "__main__":
    main()
