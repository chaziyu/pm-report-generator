#!/usr/bin/env python3
"""
CLI Tool: Trend Micro Deep Security PM Report Converter & Training Exporter.
Ingests Deep Security reports, extracts telemetry, evaluates health and version rules,
generates the official CTC Word (.docx) report, and exports SFT / few-shot training pairs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.deep_security import (
    DeepSecurityReportData,
    DeepSecuritySystemData,
    DeepSecurityServerHealth,
    DeepSecurityLicenseData,
    DeepSecurityAlertsEvents,
    DeepSecurityEvaluator,
    DeepSecurityCTCReportGenerator,
    DeepSecurityReportImporter,
    DeepSecurityParser,
)

def export_training_dataset_from_report(
    report_data: DeepSecurityReportData,
    output_jsonl: Path,
) -> None:
    """
    Exports structured training dataset pairs for AI model fine-tuning and in-context learning.
    Each record contains prompt input (Deep Security telemetry) and target structured output.
    """
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    prompt_text = (
        f"TREND MICRO DEEP SECURITY PREVENTIVE MAINTENANCE EVIDENCE:\n"
        f"Customer: {report_data.customer}\n"
        f"Model: {report_data.system.model}\n"
        f"Hostname: {report_data.system.hostname}\n"
        f"Manager Version: {report_data.system.manager_version}\n"
        f"Agent Version: {report_data.system.agent_version}\n"
        f"Server IP: {report_data.system.dsm_ip}\n"
        f"CPU Usage: {report_data.health.cpu_usage_pct}%, Memory Usage: {report_data.health.memory_usage_pct}%\n"
        f"Disk Space OK: {report_data.health.disk_space_ok}\n"
        f"License Active: {report_data.licenses.is_active}\n"
        f"Notable Alerts Found: {report_data.alerts_events.notable_alerts_found}\n"
        f"Malware Detections: {report_data.alerts_events.malware_detections}\n"
    )

    target_data = {
        "model": report_data.system.model,
        "hostname": report_data.system.hostname,
        "manager_version": report_data.system.manager_version,
        "executive_summary": {
            "key_highlights": report_data.key_highlights,
            "recommendations": [r.dict() for r in report_data.recommendations],
        },
        "checklist": [item.dict() for item in report_data.checklist],
        "appendices_count": len(report_data.appendix_images),
    }

    record = {
        "prompt": prompt_text,
        "completion": json.dumps(target_data, indent=2),
    }

    with open(output_jsonl, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Exported training sample to: {output_jsonl}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert Trend Micro Deep Security PM reports and export training pairs."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=str,
        help="Path to Deep Security DOCX report or telemetry JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="workspace/output/Deep_Security_PM_Report.docx",
        help="Path for generated CTC Word report (.docx).",
    )
    parser.add_argument(
        "--template",
        "-t",
        type=str,
        default=None,
        help="Path to custom DOCX template (defaults to templates/deep_security_pm_template.docx).",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="workspace/datasets/deep_security_pm",
        help="Target directory for imported dataset cases.",
    )
    parser.add_argument(
        "--export-training",
        type=str,
        default=None,
        help="Optional path to export supervised fine-tuning / few-shot training pairs JSONL.",
    )

    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Input path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    evaluator = DeepSecurityEvaluator()
    generator = DeepSecurityCTCReportGenerator(
        default_template=Path(args.template) if args.template else None
    )

    if input_path.suffix.lower() == ".docx":
        # Import report into dataset
        importer = DeepSecurityReportImporter(output_dir=Path(args.dataset_dir))
        print(f"Importing Deep Security DOCX report: {input_path.name}...")
        import_res = importer.import_report(input_path)
        print(f"Extracted Case ID: {import_res['case_id']}")
        print(f"Appendices extracted: {import_res['appendices_count']}")

        # Parse telemetry from expected values
        exp = import_res["expected_values"]
        parser_ds = DeepSecurityParser()
        report_data = parser_ds.parse_telemetry(exp)

        # Run rules evaluation
        evaluator.evaluate(report_data)

        # Generate output report
        out_path = Path(args.output).resolve()
        print(f"Generating CTC Deep Security Word Report: {out_path}...")
        final_doc = generator.generate_report(
            report_data=report_data,
            output_path=out_path,
        )
        print(f"Report generated successfully: {final_doc} ({final_doc.stat().st_size} bytes)")

        # Export training pairs if requested
        if args.export_training:
            jsonl_path = Path(args.export_training).resolve()
            importer.export_training_dataset(import_res["case_id"], jsonl_path)
            print(f"Exported training pairs to: {jsonl_path}")

    elif input_path.suffix.lower() == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        parser_ds = DeepSecurityParser()
        report_data = parser_ds.parse_telemetry(raw_data)
        evaluator.evaluate(report_data)

        out_path = Path(args.output).resolve()
        final_doc = generator.generate_report(
            report_data=report_data,
            output_path=out_path,
        )
        print(f"Report generated successfully: {final_doc}")

        if args.export_training:
            export_training_dataset_from_report(report_data, Path(args.export_training).resolve())

    else:
        print(f"Unsupported file extension: {input_path.suffix}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
