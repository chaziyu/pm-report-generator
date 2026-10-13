import os
import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import json

def inspect_docx(docx_path: str, verbose: bool = False):
    doc = Document(docx_path)
    report = {
        "paragraphs_count": len(doc.paragraphs),
        "tables_count": len(doc.tables),
        "sections_count": len(doc.sections),
        "tables": [],
        "appendix_paragraphs": [],
        "inline_shapes": []
    }

    # Inspect sections (headers / footers)
    sections_info = []
    for s_idx, sec in enumerate(doc.sections):
        sec_info = {
            "index": s_idx,
            "header_paragraphs": [p.text.strip() for p in sec.header.paragraphs if p.text.strip()],
            "footer_paragraphs": [p.text.strip() for p in sec.footer.paragraphs if p.text.strip()],
        }
        sections_info.append(sec_info)
    report["sections"] = sections_info

    # Inspect paragraphs
    paragraphs_info = []
    for p_idx, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if "appendix" in text.lower():
            report["appendix_paragraphs"].append({
                "index": p_idx,
                "text": text,
                "style": p.style.name if p.style else None
            })
        if text and verbose:
            paragraphs_info.append({"index": p_idx, "text": text[:100], "style": p.style.name if p.style else None})
    if verbose:
        report["paragraphs"] = paragraphs_info

    # Inspect tables
    for t_idx, table in enumerate(doc.tables):
        rows = len(table.rows)
        cols = len(table.columns) if rows > 0 else 0
        table_data = {
            "table_index": t_idx,
            "rows": rows,
            "cols": cols,
            "sample_content": [],
            "cells_with_images": []
        }

        # Scan cells for text and drawing elements (images)
        for r_idx, row in enumerate(table.rows):
            row_texts = []
            for c_idx, cell in enumerate(row.cells):
                txt = cell.text.strip().replace("\n", " ")
                # Truncate for summary
                row_texts.append(txt[:60] if len(txt) > 60 else txt)

                # Check for drawing elements in cell xml
                drawings = cell._tc.xpath(".//a:blip")
                if drawings:
                    for d in drawings:
                        embed_id = d.get(qn("r:embed"))
                        table_data["cells_with_images"].append({
                            "row": r_idx,
                            "col": c_idx,
                            "embed_id": embed_id,
                            "cell_text_prefix": txt[:50]
                        })
            table_data["sample_content"].append(row_texts)
        report["tables"].append(table_data)

    return report

def main():
    from ...config import settings
    default_path = settings.templates_dir / "preventive-maintenance.docx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default_path)
    
    if not os.path.exists(path):
        print(f"Error: File not found at {path}")
        sys.exit(1)

    print(f"Inspecting: {path}\n")
    info = inspect_docx(path, verbose=False)

    print(f"=== Document Summary ===")
    print(f"Sections: {info['sections_count']}")
    print(f"Paragraphs: {info['paragraphs_count']}")
    print(f"Tables: {info['tables_count']}")
    print(f"Appendix Paragraphs Found: {len(info['appendix_paragraphs'])}")
    for ap in info['appendix_paragraphs']:
        print(f"  P[{ap['index']}]: {ap['text']}")

    print("\n=== Table Breakdown ===")
    for t in info["tables"]:
        t_idx = t["table_index"]
        first_row = t["sample_content"][0] if t["sample_content"] else []
        img_info = f" | {len(t['cells_with_images'])} images" if t["cells_with_images"] else ""
        print(f"Table {t_idx:2d} ({t['rows']:2d}x{t['cols']:2d}{img_info}): First row -> {first_row[:3]}")

        # If table has images or is an appendix table, print more details
        if t["cells_with_images"]:
            for img in t["cells_with_images"]:
                print(f"    -> Image cell ({img['row']}, {img['col']}) [rId: {img['embed_id']}]: '{img['cell_text_prefix']}'")

if __name__ == "__main__":
    main()
