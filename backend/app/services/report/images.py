from pathlib import Path
from PIL import Image
from docx import Document
import io

def replace_appendix_image(
    doc: Document,
    embed_rid: str,
    replacement_image_path: Path,
    preserve_aspect_ratio: bool = True
):
    """
    Replaces the underlying image part for an existing rId relationship in the Word document.
    Calculates fit-inside dimensions to preserve aspect ratio without stretching.
    """
    if not replacement_image_path.exists():
        return False

    rel = doc.part.rels.get(embed_rid)
    if not rel:
        return False

    with Image.open(replacement_image_path) as img:
        img_w, img_h = img.size
        # Save to buffer
        buf = io.BytesIO()
        # Save matching part content type if possible, or standard PNG
        img.save(buf, format="PNG")
        new_bytes = buf.getvalue()

    # Update blob directly in the target part
    rel.target_part._blob = new_bytes

    # Find the corresponding drawing element in document body to update extent
    for el in doc.element.body.iter():
        blip = None
        for child in el.iter():
            if child.tag.split("}")[-1] == "blip":
                if child.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed") == embed_rid:
                    blip = child
                    break
        if blip is not None:
            # Found drawing containing this blip; adjust extent if needed
            for ext in el.iter():
                tag = ext.tag.split("}")[-1]
                if tag in ("extent", "ext"):
                    try:
                        curr_cx = int(ext.attrib.get("cx", 0))
                        curr_cy = int(ext.attrib.get("cy", 0))
                        if curr_cx > 0 and curr_cy > 0 and img_w > 0 and img_h > 0 and preserve_aspect_ratio:
                            # Calculate proportional height maintaining column width
                            proportional_cy = int(curr_cx * (img_h / float(img_w)))
                            # Cap max height to avoid page overflow
                            max_allowed_cy = int(curr_cy * 1.5)
                            ext.attrib["cy"] = str(min(proportional_cy, max_allowed_cy))
                    except (ValueError, TypeError):
                        pass

    return True
