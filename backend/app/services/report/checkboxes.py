from docx.table import _Cell
from typing import List

W14_VAL = "{http://schemas.microsoft.com/office/word/2010/wordml}val"
CHECKED_GLYPH = "\u2612"    # ☒
UNCHECKED_GLYPH = "\u2610"  # ☐

def set_cell_checkbox(cell: _Cell, selected_option: str, all_options: List[str]):
    """
    Sets the active checkbox within a table cell containing Structured Document Tag (SDT) checkboxes.
    Matches paragraphs by option text (e.g. 'Healthy', 'Unhealthy', 'N/A', 'Pass', 'Failed', etc.).
    Preserves all styles, fonts, and Word Content Control structures.
    """
    sel_clean = selected_option.strip().lower()

    for p in cell.paragraphs:
        p_text_clean = p.text.strip().lower()

        # Find if this paragraph corresponds to one of the options
        matched_opt = None
        for opt in all_options:
            if opt.lower() in p_text_clean:
                matched_opt = opt
                break

        if not matched_opt:
            continue

        is_selected = (matched_opt.lower() == sel_clean)

        # Iterate SDT elements in this paragraph
        for sdt in p._p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sdt"):
            checked_el = None
            t_el = None
            for el in sdt.iter():
                tag_name = el.tag.split("}")[-1]
                if tag_name == "checked":
                    checked_el = el
                elif tag_name == "t":
                    t_el = el

            if checked_el is not None:
                checked_el.attrib[W14_VAL] = "1" if is_selected else "0"
            if t_el is not None:
                t_el.text = CHECKED_GLYPH if is_selected else UNCHECKED_GLYPH
