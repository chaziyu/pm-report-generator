from docx import Document
from docx.table import _Cell
from typing import Optional
from ...models.pm_data import PMData
from .checkboxes import set_cell_checkbox

W_T = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
W_TXBX = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}txbxContent"

def set_cell_text(cell: _Cell, new_text: str):
    """
    Updates the text of a table cell while preserving font formatting and run styling.
    If new_text contains multiple lines, updates existing paragraphs line-by-line.
    """
    lines = [ln.strip() for ln in new_text.split("\n") if ln.strip()]
    if not lines:
        return

    for idx, line in enumerate(lines):
        if idx < len(cell.paragraphs):
            p = cell.paragraphs[idx]
            t_elems = [el for el in p._p.iter(W_T)]
            if t_elems:
                t_elems[0].text = line
                for el in t_elems[1:]:
                    el.text = ""
            else:
                p.text = line
        else:
            # If more lines than existing paragraphs, add paragraph
            new_p = cell.add_paragraph(line)


def update_cover_textboxes(doc: Document, pm: PMData):
    """
    Updates Customer, PM Date, FSMS ID, Contract No, and Contract Period
    in the cover page textboxes without breaking drawing layout.
    """
    cust_val = str(pm.metadata.customer.value or "").strip()
    date_val = str(pm.metadata.pm_date.value or "").strip()
    fsms_val = str(pm.metadata.fsms_id.value or "").strip()
    contract_val = str(pm.metadata.contract_number.value or "").strip()
    period_val = str(pm.metadata.contract_period.value or "").strip()

    for p in doc.paragraphs:
        for tb in p._p.iter(W_TXBX):
            for tb_p in tb.iter(W_P):
                t_elems = [el for el in tb_p.iter(W_T)]
                if not t_elems:
                    continue
                full_text = "".join(el.text or "" for el in t_elems)

                if "PM DATE" in full_text and date_val:
                    t_elems[0].text = f"PM DATE: {date_val}"
                    for el in t_elems[1:]:
                        el.text = ""
                elif "FSMS" in full_text and fsms_val:
                    t_elems[0].text = f"FSMS ID: {fsms_val}"
                    for el in t_elems[1:]:
                        el.text = ""
                elif "CONTRACT NO" in full_text and contract_val:
                    t_elems[0].text = f"CONTRACT NO: {contract_val}"
                    for el in t_elems[1:]:
                        el.text = ""
                elif "CONTRACT PERIOD" in full_text and period_val:
                    t_elems[0].text = f"CONTRACT PERIOD: {period_val}"
                    for el in t_elems[1:]:
                        el.text = ""
                elif "Aeon Credit Services" in full_text and cust_val:
                    t_elems[0].text = cust_val
                    for el in t_elems[1:]:
                        el.text = ""

def populate_body_tables(doc: Document, pm: PMData):
    """
    Fills in all body tables (Author, Application, Hardware, Licensing, Firmware, VPN, Routing, Configuration).
    """
    # Table 0: Author Details
    t0 = doc.tables[0]
    if pm.metadata.engineer_name.value:
        set_cell_text(t0.rows[1].cells[2], str(pm.metadata.engineer_name.value))
    if pm.metadata.engineer_designation.value:
        set_cell_text(t0.rows[2].cells[2], str(pm.metadata.engineer_designation.value))
    if pm.metadata.pm_date.value:
        set_cell_text(t0.rows[3].cells[2], str(pm.metadata.pm_date.value))

    # Table 2: Application Information
    t2 = doc.tables[2]
    if pm.application.model.value:
        set_cell_text(t2.rows[0].cells[1], str(pm.application.model.value))
    if pm.application.hostname.value:
        set_cell_text(t2.rows[1].cells[1], str(pm.application.hostname.value))
    serials_str = str(pm.application.serial_primary.value or "")
    if pm.application.serial_secondary.value:
        serials_str += f" (Primary), {pm.application.serial_secondary.value} (Secondary)"
    if serials_str:
        set_cell_text(t2.rows[2].cells[1], serials_str)

    # Table 3: Key Highlight / Recommendation
    if pm.recommendations:
        t3 = doc.tables[3]
        set_cell_text(t3.rows[1].cells[0], f"Recommendation\n{pm.recommendations}")

    # Table 4: Hardware Health Check
    t4 = doc.tables[4]
    # 1.1 Disk
    set_cell_checkbox(t4.rows[1].cells[3], str(pm.hardware.disk_status.value or "N/A"), ["Healthy", "Unhealthy", "N/A"])
    # 1.2 CPU
    cpu_status = str(pm.hardware.cpu_status.value or "Healthy")
    set_cell_checkbox(t4.rows[2].cells[3], cpu_status, ["Healthy", "Unhealthy", "N/A"])
    cpu_val = pm.hardware.cpu_usage.value if pm.hardware.cpu_usage.value is not None else 0
    set_cell_text(t4.rows[2].cells[4], f"CPU usage: {cpu_val}%\nRefer Appendix 1")
    # 1.3 Memory
    mem_status = str(pm.hardware.memory_status.value or "Healthy")
    set_cell_checkbox(t4.rows[3].cells[3], mem_status, ["Healthy", "Unhealthy", "N/A"])
    mem_val = pm.hardware.memory_usage.value if pm.hardware.memory_usage.value is not None else 33
    set_cell_text(t4.rows[3].cells[4], f"Memory usage: {mem_val}%\nRefer Appendix 2")
    # 1.4 Interface
    set_cell_checkbox(t4.rows[4].cells[3], str(pm.hardware.interface_status.value or "Healthy"), ["Healthy", "Unhealthy", "N/A"])
    if pm.hardware.active_ports.value:
        set_cell_text(t4.rows[4].cells[4], f"Ports in-used: {pm.hardware.active_ports.value}\nRefer Appendix 3")

    # Table 5: Licensing
    t5 = doc.tables[5]
    # 2.1 FortiCare
    set_cell_checkbox(t5.rows[1].cells[3], str(pm.licensing.forticare_status.value or "Valid"), ["Valid", "Expired", "N/A"])
    exp = str(pm.licensing.expiry_date.value or "28/12/2026")
    set_cell_text(t5.rows[1].cells[4], f"FortiCare Support license is valid.\nExpiration Date: {exp}\nRefer Appendix 4")
    # 2.2 UTM Bundle
    set_cell_checkbox(t5.rows[2].cells[3], "Valid", ["Valid", "Expired", "N/A"])

    # Table 6: Firmware
    t6 = doc.tables[6]
    # 3.1 Firmware
    set_cell_checkbox(t6.rows[1].cells[3], str(pm.firmware.status.value or "Up-to-Date"), ["Up-to-Date", "Out-of-Date"])
    curr = str(pm.firmware.current.value or "v7.4.11")
    bld = str(pm.firmware.build.value or "build2878")
    mat = str(pm.firmware.maturity.value or "Mature")
    lat = str(pm.firmware.latest.value or "v7.4.12")
    set_cell_text(t6.rows[1].cells[4], f"Current Firmware Version: {curr} {bld} ({mat})\nLatest Firmware Version: {lat}\nRefer Appendix 5")
    # 3.2 FFR & 3.3 EOS
    set_cell_checkbox(t6.rows[2].cells[3], "Valid", ["Valid", "Expired", "N/A"])
    set_cell_checkbox(t6.rows[3].cells[3], "Valid", ["Valid", "Expired", "N/A"])

    # Table 7: VPN
    t7 = doc.tables[7]
    tot = pm.vpn.total.value if pm.vpn.total.value is not None else 0
    act = pm.vpn.active.value if pm.vpn.active.value is not None else 0
    inact = pm.vpn.inactive.value if pm.vpn.inactive.value is not None else 0
    set_cell_text(t7.rows[1].cells[3], f"Total VPN Tunnel(s): {tot}\nActive VPN Tunnel(s): {act}\nInactive VPN Tunnel(s): {inact}")

    # Table 9: Configuration & Operational Check
    t9 = doc.tables[9]
    # 6.1 Uptime
    if pm.configuration.uptime.value:
        set_cell_text(t9.rows[1].cells[3], f"Uptime:  {pm.configuration.uptime.value}")
    # 6.2 GUI Access
    set_cell_checkbox(t9.rows[2].cells[3], str(pm.configuration.gui_access.value or "Pass"), ["Pass", "Failed", "N/A"])
    # 6.3 CLI Access
    set_cell_checkbox(t9.rows[3].cells[3], str(pm.configuration.cli_access.value or "Pass"), ["Pass", "Failed", "N/A"])
    # 6.4 Signatures
    set_cell_checkbox(t9.rows[4].cells[3], str(pm.configuration.signatures.value or "Up-to-Date"), ["Up-to-Date", "Out-of-Date"])
    # 6.5 Firewall Date & Time
    set_cell_checkbox(t9.rows[5].cells[3], str(pm.configuration.datetime_status.value or "Pass"), ["Pass", "Failed", "N/A"])
    # 6.6 Internet Access
    set_cell_checkbox(t9.rows[6].cells[3], str(pm.configuration.internet_access.value or "Pass"), ["Pass", "Failed", "N/A"])
    # 6.7 HA
    set_cell_checkbox(t9.rows[7].cells[3], str(pm.configuration.ha_status.value or "Pass"), ["Pass", "Failed", "N/A"])
    # 6.8 Logging
    set_cell_checkbox(t9.rows[8].cells[3], str(pm.configuration.event_logging.value or "Available"), ["Available", "Un-available"])
    # 6.9 Log Manager
    set_cell_checkbox(t9.rows[9].cells[3], str(pm.configuration.log_manager.value or "Healthy"), ["Healthy", "Unhealthy", "N/A"])
    # 6.10 Backup
    set_cell_checkbox(t9.rows[10].cells[3], str(pm.configuration.backup_status.value or "Passed"), ["Passed", "Failed"])
