"""
CLI utility to batch import completed FortiGate PM reports into a local validation dataset.

Usage:
    python -m backend.tools.import_pm_reports --input private_pm_reports
    python -m tools.import_pm_reports --input ../private_pm_reports
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend and project root to sys.path if not present
tools_dir = Path(__file__).resolve().parent
backend_dir = tools_dir.parent
project_root = backend_dir.parent

for p in [str(backend_dir), str(project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Reconfigure stdout to utf-8 if supported to allow checkmark / warning glyphs
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import settings
from app.services.dataset.report_importer import ReportImporter

CHECK_MARK = "✓"
WARN_MARK = "⚠"
CROSS_MARK = "✗"
SKIP_MARK = "⊘"

def format_mark(mark: str) -> str:
    try:
        mark.encode(sys.stdout.encoding or "utf-8")
        return mark
    except Exception:
        if mark == CHECK_MARK:
            return "[OK]"
        elif mark == WARN_MARK:
            return "[WARN]"
        elif mark == CROSS_MARK:
            return "[FAIL]"
        elif mark == SKIP_MARK:
            return "[SKIP]"
        return mark

def main():
    parser = argparse.ArgumentParser(
        description="Batch import completed FortiGate PM reports into a structured local validation dataset."
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to a completed .docx report file or directory containing .docx reports."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(settings.datasets_dir),
        help=f"Target directory for imported dataset (default: {settings.datasets_dir})."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing cases if identical report SHA-256 is detected."
    )
    parser.add_argument(
        "--copy-source",
        action="store_true",
        help="Copy source DOCX into case_<id>/source/ directory."
    )

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Collect files
    if input_path.is_file():
        docx_files = [input_path]
    else:
        docx_files = sorted([
            p for p in input_path.glob("*.docx")
            if not p.name.startswith("~$")
        ])

    count = len(docx_files)
    if count == 0:
        print(f"No DOCX reports found in: {input_path}")
        sys.exit(0)

    print(f"\nFound {count} DOCX report{'s' if count != 1 else ''}\n")

    importer = ReportImporter(
        output_dir=output_dir,
        overwrite=args.overwrite,
        copy_source=args.copy_source
    )

    summary, results = importer.import_batch(input_path)

    cases_with_warnings = 0

    for idx, res in enumerate(results, 1):
        report_name = res.get("report", "unknown")
        status = res.get("status")

        print(f"[{idx}/{count}] {report_name}")

        if status == "imported":
            apps = res.get("appendices_found", 0)
            imgs = res.get("screenshots_extracted", 0)
            w_count = res.get("warnings_count", 0)
            if w_count > 0:
                cases_with_warnings += 1

            print(f"  {format_mark(CHECK_MARK)} {apps} appendix sections found")
            print(f"  {format_mark(CHECK_MARK)} {imgs} screenshot images extracted")
            print(f"  {format_mark(CHECK_MARK)} expected values extracted")
            if w_count > 0:
                print(f"  {format_mark(WARN_MARK)} {w_count} warning{'s' if w_count != 1 else ''} / unresolved field{'s' if w_count != 1 else ''}")
                for w in res.get("warnings", [])[:3]:
                    print(f"      - {w}")
                if len(res.get("warnings", [])) > 3:
                    print(f"      - ... and {len(res.get('warnings', [])) - 3} more")

        elif status == "duplicate":
            print(f"  {format_mark(SKIP_MARK)} Duplicate detected (already imported in {res.get('case_id')})")

        elif status == "unsupported_template_variant":
            print(f"  {format_mark(SKIP_MARK)} Unsupported template variant: {res.get('reason')}")

        elif status == "failed":
            print(f"  {format_mark(CROSS_MARK)} Import failed: {res.get('error')}")

        print()

    print("Import complete\n")
    print(f"Cases imported:                {summary.reports_imported}")
    print(f"Cases with warnings:           {cases_with_warnings}")
    print(f"Duplicate reports skipped:     {summary.duplicate_reports}")
    print(f"Unsupported variants skipped:  {summary.unsupported_template_variants}")
    print(f"Failed imports:                {summary.reports_failed}")
    print(f"Output:")
    print(f"{output_dir}\n")

    if summary.reports_failed > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
