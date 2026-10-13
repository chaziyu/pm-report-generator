# FortiGate PM Report Generator

Automated, deterministic FortiGate Preventive Maintenance (PM) report generator designed for confidential, local-first execution.

The application ingests unlabelled firewall screenshots, extracts telemetry, classifies evidence into the fixed 16-appendix structure, executes PM health rules, and compiles the final official Word (`.docx`) report directly from the pristine corporate template without altering styles, logos, headers, footers, or layout.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     Localhost Web UI                        │
│                  http://localhost:5173                      │
│                                                             │
│  New PM → Upload → Analyze → Review → Generate → Download   │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                   http://localhost:8000                     │
├─────────────────────────────────────────────────────────────┤
│ Session Manager (workspace/<session_id>/)                  │
│ Screenshot Ingestion & EXIF Normalization                   │
│ Duplicate Detection (SHA-256 exact + dHash perceptual)      │
│ Offline Windows Media OCR (word bounding boxes)             │
│ Weighted Anchor Screenshot Classifier (16 Categories)       │
│ Auto-Crop Container Detection                               │
│ Master Structured Telemetry Extractor                       │
│ Deterministic PM Rules Engine (Health, Thresholds, VPN)     │
│ Pre-Generation Cross-Field Consistency Validator            │
│ Non-Destructive In-Place DOCX Generator                    │
└─────────────┬───────────────────────┬───────────────────────┘
              │                       │
              ▼                       ▼
     Local workspace           Template repository
     screenshots / JSON        pristine DOCX
     crops / reports
```

---

## 16-Appendix Structure

The report enforces deterministic appendix mapping matching FortiGate PM requirements:

1. **Appendix 1**: CPU Usage
2. **Appendix 2**: Memory Usage
3. **Appendix 3**: Interface Monitoring
4. **Appendix 4**: FortiCare & Feature Licensing
5. **Appendix 5**: Firmware Version & Build
6. **Appendix 6**: VPN Tunnels (Total / Active / Inactive)
7. **Appendix 7**: Static Routes & Routing Table
8. **Appendix 8**: Firewall System Uptime
9. **Appendix 9**: Access via GUI / Web Browser
10. **Appendix 10**: Access via CLI / SSH
11. **Appendix 11**: Signatures & Definitions Version
12. **Appendix 12**: Firewall Date & Time (NTP Sync)
13. **Appendix 13**: High Availability (HA) Status
14. **Appendix 14**: System Event Log
15. **Appendix 15**: Log Manager (FortiAnalyzer / FortiCloud)
16. **Appendix 16**: Backup Configuration

---

## Quickstart Guide

### One-Click Startup (Recommended)

Simply double-click [`start.bat`](file:///c:/Users/ziyu.cha-c/Documents/GitHub/pm-report-generator/start.bat) or run in terminal:

```cmd
start.bat
```

This will automatically:
1. Verify the Python virtual environment and frontend `node_modules`.
2. Launch the FastAPI backend on `http://localhost:8000`.
3. Launch the Vite React frontend on `http://localhost:5173`.
4. Open your default web browser directly to `http://localhost:5173`.

To stop both services at any time, run [`stop.bat`](file:///c:/Users/ziyu.cha-c/Documents/GitHub/pm-report-generator/stop.bat).

---

### Manual Setup (Optional)

```powershell
cd backend
# Create virtual environment if not already present
python -m venv venv
# Activate and install dependencies
.\venv\Scripts\pip install -r requirements.txt
# Run the FastAPI server
.\venv\Scripts\python run.py
```

Backend will be accessible at `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

### 2. Frontend Setup

```powershell
cd frontend
# Install dependencies
npm.cmd install
# Run development server
npm.cmd run dev
```

Frontend will run on `http://localhost:5173`.

### 3. Running Tests

```powershell
cd backend
# Run end-to-end pipeline test
.\venv\Scripts\python -m tests.test_e2e_pipeline

# Run dataset importer tests
.\venv\Scripts\python -m unittest tests.test_dataset_importer
```

---

## Batch PM Report Dataset Importer

The Batch PM Report Dataset Importer extracts embedded appendix screenshots and expected report values directly from completed FortiGate PM `.docx` reports to build a structured local ground-truth dataset for validating OCR, classification, and extraction pipelines.

### Usage

1. **Place completed PM reports** in a local directory (e.g. `private_pm_reports/`):
   ```text
   private_pm_reports/
       report_001.docx
       report_002.docx
   ```

2. **Run the importer CLI**:
   ```powershell
   # From project root:
   .\backend\venv\Scripts\python -m backend.tools.import_pm_reports --input private_pm_reports

   # Or from backend directory:
   cd backend
   .\venv\Scripts\python -m tools.import_pm_reports --input ..\private_pm_reports
   ```

   **Optional Flags**:
   - `--output <dir>`: Custom destination directory (default: `workspace/datasets/pm_reports`).
   - `--overwrite`: Re-import and overwrite existing cases if identical report SHA-256 is detected.
   - `--copy-source`: Copy the source `.docx` into `case_<id>/source/`.

3. **Output Dataset Structure**:
   Generated in `workspace/datasets/pm_reports/`:
   ```text
   workspace/datasets/pm_reports/
       case_<id>/
           images/
               extracted_image_001.png
               ...
           appendices/
               appendix_01_cpu.png
               appendix_02_memory.png
               appendix_07_01.png
               appendix_07_02.png
               ...
           expected.json
           manifest.json
       dataset.json
       import_summary.json
   ```

### Important Security & Privacy Notice

- **Strict Local & Offline Execution**: No external AI APIs, cloud calls, or network telemetry are used.
- **Source Report Immutability**: All source reports are read-only. SHA-256 hashes are verified before and after import to guarantee source files remain completely untouched.
- **Customer Confidentiality**: Extracted screenshots and reports contain customer IP addresses, hostnames, and network topology.
- **Git Protection**: `private_pm_reports/`, `workspace/datasets/`, and `backend/tests/fixtures/private/` are strictly excluded in `.gitignore` and **must never be committed to Git**.

---

## Local AI Fallback Subsystem (Qwen3-1.7B)

The application incorporates an optional, fully-offline AI interpretation and verification layer powered by `Qwen3-1.7B-Q4_K_M.gguf` running on a managed, bundled `llama.cpp` (`llama-server`) process on Windows.

### Architectural Highlights

- **Deterministic-First**: Native Windows OCR, regex extraction, and anchor classifiers remain primary. Qwen is invoked only when screenshots exhibit semantic ambiguity (e.g. multi-widget System Info dashboards containing both firmware and uptime) or uncertain confidence.
- **Strict Identity Safety**: Serial numbers and hostnames are guarded by explicit arbitration rules. Local AI suggestions **never** silently overwrite OCR values; disagreements trigger `DISAGREEMENT` and enforce manual confirmation.
- **Lazy Startup & Idle Shutdown**: `llama-server` is not loaded into memory at startup. It starts on-demand and shuts down after 5 minutes of inactivity to release RAM.
- **Single Concurrency Lock**: Inference is limited to concurrency = 1 with dynamic context allocation (2048 tokens for <= 8 GB RAM; 4096 tokens for > 8 GB RAM).
- **Packaging Architecture**: Supports Full Offline Installer (`PMReportGenerator-Offline-Setup.exe` with pre-bundled GGUF) and Light Installer (`PMReportGenerator-Setup.exe` with atomic hash-verified first-run download).

See [`doc/local_ai_architecture_and_packaging.md`](doc/local_ai_architecture_and_packaging.md) for full architecture and packaging details.

---

## Security & Confidentiality

- **100% Offline & Local**: Built on native Windows Media OCR (`Windows.Media.Ocr`) and local-only `llama.cpp` inference bound strictly to `127.0.0.1`.
- **No Cloud Services**: Zero external API calls, zero telemetry, zero unauthenticated inbound ports.
- **Template Integrity**: Preserves Word Structured Document Tags (`<w:sdt>`) for checkboxes (☒ / ☐) and replaces relationship blobs directly so Microsoft Word opens the file with no repair warnings.

