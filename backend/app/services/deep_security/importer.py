"""
Dataset Importer & Telemetry Extractor for Trend Micro Deep Security PM Reports.
Extracts embedded screenshots, metadata, checklist evaluations, and builds
manifest.json, expected.json, and training dataset pairs (training_pairs.jsonl).
"""

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import docx
from docx import Document
from docx.oxml.ns import qn
from PIL import Image

W_TXBX = qn("w:txbxContent")
W_P = qn("w:p")
W_T = qn("w:t")

DEEP_SECURITY_APPENDIX_MAP: Dict[int, Dict[str, str]] = {
    1: {"slug": "dashboard", "title": "Dashboard and Widgets"},
    2: {"slug": "alerts", "title": "Alerts"},
    3: {"slug": "events_reports", "title": "Events and Reports"},
    4: {"slug": "license_status", "title": "License Status"},
    5: {"slug": "agent_inventory", "title": "Agent Inventory Management"},
    6: {"slug": "server_updates", "title": "Deep Security Server Updates Status"},
    7: {"slug": "system_info", "title": "Deep Security Manager System Information"},
    8: {"slug": "agent_software_update", "title": "Deep Security Agent Software Update"},
    9: {"slug": "server_health", "title": "Deep Security Manager and Database Server Health Check"},
}

def calculate_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class DeepSecurityReportImporter:
    """
    Extracts structured ground truth and screenshot evidence from Deep Security reports.
    """

    def __init__(self, output_dir: Path, overwrite: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.overwrite = overwrite

    def import_report(self, docx_path: Path) -> Dict[str, Any]:
        docx_path = Path(docx_path)
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")

        sha = calculate_sha256(docx_path)
        doc = Document(str(docx_path))

        # 1. Extract metadata and expected values
        expected_values = self.extract_expected_values(doc)

        fsms_id = expected_values.get("metadata", {}).get("fsms_id") or sha[:8]
        case_id = f"case_{fsms_id}_deep_security"
        case_dir = self.output_dir / case_id

        if case_dir.exists() and not self.overwrite:
            return {"case_id": case_id, "status": "skipped", "path": str(case_dir)}

        images_dir = case_dir / "images"
        appendices_dir = case_dir / "appendices"
        images_dir.mkdir(parents=True, exist_ok=True)
        appendices_dir.mkdir(parents=True, exist_ok=True)

        # 2. Extract media from docx zip
        extracted_media = self._extract_media(docx_path, images_dir)

        # 3. Map images to appendices
        appendix_manifest = self._map_images_to_appendices(doc, extracted_media, appendices_dir)

        # 4. Save manifest and expected values
        manifest = {
            "case_id": case_id,
            "source_report": docx_path.name,
            "source_sha256": sha,
            "template_variant": "trend_micro_deep_security_pm_v1",
            "metadata": expected_values["metadata"],
            "application": expected_values["application"],
            "appendices": appendix_manifest,
        }

        with open(case_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        with open(case_dir / "expected.json", "w", encoding="utf-8") as f:
            json.dump(expected_values, f, indent=2)

        # Update dataset.json in output_dir
        self._update_dataset_index(case_id, docx_path.name, expected_values, sha, len(appendix_manifest))

        return {
            "case_id": case_id,
            "case_dir": str(case_dir),
            "source_sha256": sha,
            "expected_values": expected_values,
            "appendices_count": len(appendix_manifest),
        }

    def extract_expected_values(self, doc: Document) -> Dict[str, Any]:
        """Extracts expected fields, checklist results, highlights, and recommendations."""
        data: Dict[str, Any] = {
            "metadata": {
                "customer": "LQ Retail Sdn Bhd",
                "pm_date": None,
                "fsms_id": None,
                "contract_no": None,
                "contract_period": None,
                "author_name": None,
                "author_designation": None,
                "author_date": None,
                "verified_name": None,
                "verified_designation": None,
                "verified_date": None,
            },
            "application": {
                "model": "Deep Security",
                "hostname": None,
                "manager_version": None,
                "agent_version": None,
            },
            "executive_summary": {
                "key_highlights": [],
                "recommendations": [],
            },
            "checklist": [],
        }

        # 1. Textboxes (Cover)
        for p in doc.paragraphs[:30]:
            for tb in p._p.iter(W_TXBX):
                for tb_p in tb.iter(W_P):
                    txt = "".join(el.text or "" for el in tb_p.iter(W_T)).strip()
                    if not txt:
                        continue
                    if "The Exchange TRX" in txt or "LQ Retail" in txt:
                        data["metadata"]["customer"] = txt
                    m_date = re.search(r"PM DATE\s*:\s*([0-9/]+)", txt, re.IGNORECASE)
                    if m_date:
                        data["metadata"]["pm_date"] = m_date.group(1).strip()
                    m_fsms = re.search(r"FSMS ID\s*:\s*([0-9]+)", txt, re.IGNORECASE)
                    if m_fsms:
                        data["metadata"]["fsms_id"] = m_fsms.group(1).strip()
                    m_cnt = re.search(r"Contract No\s*:\s*([^\s]+)", txt, re.IGNORECASE)
                    if m_cnt:
                        data["metadata"]["contract_no"] = m_cnt.group(1).strip()
                    m_per = re.search(r"Contract Period\s*:\s*(.+)", txt, re.IGNORECASE)
                    if m_per:
                        data["metadata"]["contract_period"] = m_per.group(1).strip()

        # 2. Table 0 (Author Details)
        if len(doc.tables) > 0:
            t0 = doc.tables[0]
            for r_idx, r in enumerate(t0.rows):
                if len(r.cells) >= 2:
                    lbl = r.cells[0].text.strip().lower()
                    val = r.cells[1].text.strip()
                    if lbl == "name" and r_idx < 5:
                        data["metadata"]["author_name"] = val
                    elif lbl == "designation" and r_idx < 5:
                        data["metadata"]["author_designation"] = val
                    elif lbl == "date" and r_idx < 5:
                        data["metadata"]["author_date"] = val
                    elif lbl == "name" and 5 <= r_idx < 10:
                        data["metadata"]["verified_name"] = val
                    elif lbl == "designation" and 5 <= r_idx < 10:
                        data["metadata"]["verified_designation"] = val
                    elif lbl == "date" and 5 <= r_idx < 10:
                        data["metadata"]["verified_date"] = val

        # 3. Table 2 (Appliance Information)
        if len(doc.tables) > 2:
            t2 = doc.tables[2]
            for r in t2.rows:
                if len(r.cells) >= 2:
                    lbl = r.cells[0].text.strip().lower()
                    val = r.cells[1].text.strip()
                    if "model" in lbl:
                        data["application"]["model"] = val
                    elif "hostname" in lbl:
                        data["application"]["hostname"] = val

        # 4. Table 3 (Executive Summary)
        if len(doc.tables) > 3:
            t3 = doc.tables[3]
            cell = t3.rows[0].cells[0]
            paras = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
            in_rec = False
            for p_txt in paras:
                if "key highlight" in p_txt.lower():
                    continue
                if "recommendation" in p_txt.lower():
                    in_rec = True
                    continue
                if not in_rec:
                    data["executive_summary"]["key_highlights"].append(p_txt)
                else:
                    data["executive_summary"]["recommendations"].append(p_txt)

        # 5. Table 4 (Item 1 Version)
        if len(doc.tables) > 4:
            t4 = doc.tables[4]
            for r in t4.rows:
                if len(r.cells) >= 3 and r.cells[0].text.strip() == "1":
                    desc = r.cells[2].text.strip()
                    m_v = re.search(r"version/build:\s*([0-9\.]+)", desc, re.IGNORECASE)
                    if m_v:
                        data["application"]["manager_version"] = m_v.group(1).strip()

        # 6. Tables 5, 6, 7 (Checklist)
        for t_idx in [5, 6, 7]:
            if t_idx < len(doc.tables):
                t = doc.tables[t_idx]
                curr_item_no = None
                curr_item_task = None
                for r in t.rows:
                    if len(r.cells) >= 6:
                        c0 = r.cells[0].text.strip()
                        c1 = r.cells[1].text.strip()
                        if c0.isdigit():
                            curr_item_no = int(c0)
                            curr_item_task = c1
                        elif c1 and not c0:
                            # Subtask row
                            c2 = r.cells[2].text.strip()
                            c3 = r.cells[3].text.strip()
                            c4 = r.cells[4]
                            c5 = r.cells[5].text.strip()

                            # Read FORMCHECKBOX state
                            res = "Yes"
                            cbs = c4._tc.xpath(".//w:checkBox")
                            if len(cbs) >= 2:
                                def0 = cbs[0].find(qn("w:default"))
                                if def0 is not None and def0.attrib.get(qn("w:val")) == "true":
                                    res = "Yes"
                                else:
                                    res = "No"

                            data["checklist"].append({
                                "item_no": curr_item_no,
                                "section": curr_item_task,
                                "task": c1,
                                "expected_input": c2,
                                "expected_output": c3,
                                "result": res,
                                "remarks": c5,
                            })

        return data

    def _extract_media(self, docx_path: Path, output_dir: Path) -> Dict[str, Path]:
        extracted = {}
        with zipfile.ZipFile(docx_path, "r") as z:
            for name in z.namelist():
                if name.startswith("word/media/"):
                    fname = Path(name).name
                    target = output_dir / fname
                    with open(target, "wb") as f:
                        f.write(z.read(name))
                    extracted[f"media/{fname}"] = target
        return extracted

    def _map_images_to_appendices(
        self,
        doc: Document,
        extracted_media: Dict[str, Path],
        appendices_dir: Path
    ) -> Dict[str, Any]:
        img_rels = {r_id: rel.target_ref for r_id, rel in doc.part.rels.items() if "image" in rel.target_ref}

        # Track which appendix header we are currently under
        curr_app_no = None
        appendix_manifest: Dict[str, Any] = {}

        for p in doc.paragraphs:
            txt = p.text.strip()
            # Detect Appendix X
            m_app = re.search(r"appendix\s*([0-9]+)", txt, re.IGNORECASE)
            if m_app:
                curr_app_no = int(m_app.group(1))

            blips = p._p.xpath(".//a:blip")
            if blips and curr_app_no in DEEP_SECURITY_APPENDIX_MAP:
                app_info = DEEP_SECURITY_APPENDIX_MAP[curr_app_no]
                app_key = str(curr_app_no)
                if app_key not in appendix_manifest:
                    appendix_manifest[app_key] = {
                        "appendix": curr_app_no,
                        "title": app_info["title"],
                        "slug": app_info["slug"],
                        "images": [],
                    }

                for b in blips:
                    r_id = b.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                    rel_target = img_rels.get(r_id, "")
                    src_file = extracted_media.get(rel_target)
                    if src_file and src_file.exists():
                        img_idx = len(appendix_manifest[app_key]["images"]) + 1
                        dest_name = f"appendix_{curr_app_no:02d}_{app_info['slug']}_{img_idx:02d}.png"
                        dest_path = appendices_dir / dest_name
                        shutil.copyfile(src_file, dest_path)
                        appendix_manifest[app_key]["images"].append({
                            "original": src_file.name,
                            "saved_as": dest_name,
                            "path": str(dest_path),
                        })

        return appendix_manifest

    def _update_dataset_index(
        self,
        case_id: str,
        report_name: str,
        expected: Dict[str, Any],
        sha: str,
        app_count: int,
    ) -> None:
        index_file = self.output_dir / "dataset.json"
        index = {"cases": []}
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = {"cases": []}

        # Filter out existing
        index["cases"] = [c for c in index.get("cases", []) if c.get("case_id") != case_id]
        index["cases"].append({
            "case_id": case_id,
            "report": report_name,
            "model": expected.get("application", {}).get("model", "Deep Security"),
            "hostname": expected.get("application", {}).get("hostname", "DSM-GF-MSER-01"),
            "appendix_count": app_count,
            "source_sha256": sha,
        })

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def export_training_dataset(self, case_id: str, output_jsonl: Path) -> Path:
        """
        Exports supervised fine-tuning (SFT) / few-shot training pairs in JSONL format.
        """
        case_dir = self.output_dir / case_id
        if not case_dir.exists():
            raise FileNotFoundError(f"Case directory not found: {case_dir}")

        with open(case_dir / "expected.json", "r", encoding="utf-8") as f:
            expected = json.load(f)
        with open(case_dir / "manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)

        app = expected.get("application", {})
        meta = expected.get("metadata", {})
        exec_sum = expected.get("executive_summary", {})

        # Build prompt representation of raw telemetry and screenshot evidence
        prompt_text = (
            f"TREND MICRO DEEP SECURITY TELEMETRY & PM EVIDENCE:\n"
            f"Customer: {meta.get('customer')}\n"
            f"Hostname: {app.get('hostname')}\n"
            f"Model: {app.get('model')}\n"
            f"Deep Security Manager Version: {app.get('manager_version')}\n"
            f"Contract: {meta.get('contract_no')} ({meta.get('contract_period')})\n"
            f"Date of PM: {meta.get('pm_date')}\n"
            f"Evidence: Dashboard, Alerts, Events & Reports, License Status, Agent Inventory, "
            f"Server Updates, System Information, Agent Software Update, Server Health Check.\n"
        )

        target_data = {
            "model": app.get("model"),
            "hostname": app.get("hostname"),
            "manager_version": app.get("manager_version"),
            "executive_summary": {
                "key_highlights": exec_sum.get("key_highlights", []),
                "recommendations": exec_sum.get("recommendations", []),
            },
            "checklist": expected.get("checklist", []),
            "appendices_count": len(manifest.get("appendices", {})),
        }

        record = {
            "prompt": prompt_text,
            "completion": json.dumps(target_data, indent=2),
        }

        output_jsonl = Path(output_jsonl)
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "w", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return output_jsonl
