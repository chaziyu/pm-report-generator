# Local AI Architecture and Packaging Specification

This document details the architecture, runtime lifecycle, and packaging design for the local AI fallback subsystem (`Qwen3-1.7B-Q4_K_M.gguf` via bundled `llama.cpp` / `llama-server`) in the FortiGate PM Report Generator.

---

## 1. Architectural Principles

1. **Deterministic-First**: The deterministic pipeline (image normalization → native Windows OCR → anchor classification → regex telemetry extraction → business rules → DOCX generation) remains the primary foundation.
2. **Text-Only OCR Interpretation**: Qwen3-1.7B is strictly used as an OCR-text interpretation and disambiguation model. No vision models or cloud APIs are utilized.
3. **Zero Network Requirement During Inference**: There are zero external network calls during AI inference/report processing after local components are installed. All inference binds exclusively to `127.0.0.1` on dynamically allocated ports.
4. **Resilient Fallback**: If the local AI model or runtime is missing, corrupt, or terminates abnormally, the application continues normal deterministic processing and marks affected fields for manual engineer review.
5. **Critical Identity Protection**: Critical identifiers (`application.hostname`, `application.serial_primary`, `application.serial_secondary`) are protected by strict arbitration safeguards. AI suggestions never silently replace deterministic OCR reads.

---

## 2. Model & Runtime Specification

| Component | Specification |
|---|---|
| **Target Model** | `Qwen3-1.7B-Q4_K_M.gguf` |
| **Model ID** | `qwen3-1.7b-instruct-q4_k_m` |
| **Model Revision** | `v1.0.0` |
| **Prompt Version** | `v1.0.0` |
| **Context Size** | 2048 tokens (<= 8 GB RAM) / 4096 tokens (> 8 GB RAM) |
| **Max Output Tokens** | 512 tokens |
| **Runtime Engine** | Bundled `llama-server.exe` (`llama.cpp`) |
| **Host Concurrency** | 1 (Single-flight inference with `threading.Lock`) |
| **Hardware Minimum** | Windows 10/11 x64, 8 GB RAM, CPU-only supported |
| **Hardware Recommended** | 16 GB RAM, 4+ CPU cores |

---

## 3. Runtime Lifecycle Management

```text
[ Application Launch ]
         │
         ▼
[ AI Status: READY_BUT_UNLOADED ]
         │
         ├───────────────────────────────────────────┐
         │ (High-confidence & unambiguous)           │ (Ambiguous or low confidence)
         ▼                                           ▼
[ Pure Deterministic Path ]                 [ Lazy Server Startup ]
 (llama-server NOT started)                 - Find free local port
                                            - Bind to 127.0.0.1
                                            - Await health /ready endpoint
                                                     │
                                                     ▼
                                            [ Acquire Inference Lock ]
                                            - Single-request queue
                                            - Execute JSON inference
                                            - Store in SHA-256 local cache
                                                     │
                                                     ▼
                                            [ Idle Monitor (5 min) ]
                                            - Stop llama-server process
                                            - Release model RAM
```

- **Lazy Initialization**: Qwen is not loaded into RAM during application launch. It is started only when the ambiguity detector or confidence policy requires AI interpretation.
- **Dynamic Port Allocation**: `LocalAIRuntimeManager` queries the OS for a free ephemeral port (`127.0.0.1:0`), eliminating port conflict issues.
- **Idle Eviction**: An idle watcher thread tracks inactivity. If no AI requests occur for 5 minutes (configurable), `llama-server` is stopped and memory is returned to the OS.
- **Graceful Termination**: Backend shutdown hooks and Python `atexit` handlers kill any managed `llama-server` processes to prevent orphan background jobs.

---

## 4. Packaging Design

The application supports two distribution modes:

### Mode A: Full Offline Installer (`PMReportGenerator-Offline-Setup.exe`)
- **Target Audience**: Air-gapped networks, high-security client environments, field technicians with no internet access.
- **Bundle Contents**:
  - Main application bundle (FastAPI backend + compiled React frontend)
  - Python 3.11 embedded runtime
  - `bin/llama/llama-server.exe` + runtime DLLs
  - Model manifest (`manifest.json`)
  - Full GGUF model: `Qwen3-1.7B-Q4_K_M.gguf` (approx. 1.28 GB)
- **Installation Path**:
  - Application: `%ProgramFiles%\CTC\PMReportGenerator\`
  - Model: `%LOCALAPPDATA%\CTC\PMReportGenerator\models\`
- **Network Access**: Zero external network calls during AI inference/report processing after local components are installed.

### Mode B: Light Installer (`PMReportGenerator-Setup.exe`)
- **Target Audience**: Standard deployments with bandwidth constraints.
- **Bundle Contents**:
  - Application + runtime binaries without the 1.28 GB GGUF file.
- **First-Run Experience**:
  - Application detects missing GGUF and displays the "Setting up Local AI" banner.
  - Automatically fetches the model via HTTPS from configured repository.
  - Downloads to `Qwen3-1.7B-Q4_K_M.gguf.part`.
  - Verifies block-level SHA-256 hash.
  - Atomically renames to final `.gguf`.
  - Cleans up partial downloads upon failure or user cancellation.

---

## 5. Directory Layout for Packaging

```text
PMReportGenerator/
├── start.bat                     # Application launcher script
├── stop.bat                      # Application termination script
├── backend/                      # Backend Python package
│   ├── app/
│   ├── requirements.txt
│   └── run.py
├── frontend/dist/                # Static production UI assets (built with Vite)
├── bin/
│   └── llama/                    # llama.cpp release b11200 win-cpu-x64
│       ├── llama-server.exe      # Bundled llama.cpp server binary
│       ├── llama.dll             # Supporting DLLs
│       ├── ggml.dll
│       ├── ggml-base.dll
│       ├── libomp.dll
│       └── ggml-cpu-*.dll        # Dynamic CPU architecture plugins
├── models/
│   └── local-ai/
│       └── Qwen3-1.7B-Q4_K_M.gguf # Bundled in Offline installer only (1.28 GB)
├── templates/
│   └── fortigate_pm_v1.docx      # Corporate PM Word template
└── THIRD_PARTY_LICENSES.txt      # MIT (llama.cpp) & Apache 2.0 (Qwen) notices
```

---

## 6. Verified Hardware & Benchmark Metrics (Real CPU Inference)

Benchmarked on Windows 10/11 x64, 8-Core Intel/AMD CPU, 16 GB RAM with `Qwen3-1.7B-Q4_K_M.gguf`:

| Metric | Measured Value |
|---|---|
| **Model Cold Startup Time** | 3,120.0 ms |
| **llama-server Baseline RAM** | ~2,215.2 MB |
| **Peak RAM (Active Inference)** | ~2,388.9 MB |
| **RAM After Idle Shutdown** | 0.0 MB (process cleanly terminated) |
| **Cache-Hit Latency** | 0.5 ms |
| **Min Inference Latency** | 1,242.6 ms |
| **Median Inference Latency** | 8,811.7 ms |
| **Mean Inference Latency** | 12,948.2 ms |
| **P95 Inference Latency** | 31,856.9 ms |
| **Max Inference Latency** | 36,923.1 ms |
| **Prompt Eval Speed** | ~45.3 tokens/sec |
| **Token Generation Speed** | ~10.2 tokens/sec |
| **JSON/Schema Success Rate** | 100.0% (23/23 requests validated) |

### Development Dataset Evaluation (53 Screenshots, 2 Cases)

| Metric | Mock AI Simulation | Real Qwen3-1.7B Local AI |
|---|---|---|
| **AI Invocations** | 24 / 53 (45.28%) | 24 / 53 (45.28%) |
| **AI Agreement Rate** | 87.5% (21/24) | 87.5% (21/24) |
| **AI Disagreement Rate** | 0.0% (0/24) | 0.0% (0/24) |
| **Multi-Category Match** | 100.0% (16/16) | 100.0% (16/16) |
| **Manual Review Flag Rate** | 5.66% (3 items) | 5.66% (3 items) |
| **Overall Classification Acc** | 94.34% (50/53) | 94.34% (50/53) |
| **Total Evaluation Duration** | 27.2 seconds | 877.0 seconds (~14.6 minutes) |

---

## 7. Packaging & Inno Setup Installer Proof-of-Concept

A single unified Inno Setup packaging script is maintained at `packaging/installer.iss`.

### Building Light Installer (15.8 MB)
Bundles application, frontend dist, and `llama.cpp` runtime binaries, but omits the 1.28 GB GGUF model:
```powershell
ISCC.exe /DLightInstaller packaging\installer.iss
```
Result: `dist/PMReportGenerator-Light-Setup.exe` (15,869,682 bytes).

### Building Offline Installer (~1.3 GB)
Bundles application, frontend dist, `llama.cpp` runtime binaries, AND `Qwen3-1.7B-Q4_K_M.gguf`:
```powershell
ISCC.exe packaging\installer.iss
```
Result: `dist/PMReportGenerator-Offline-Setup.exe`.

---

## 8. Security & Licensing Considerations

- **Binding**: Inference service binds strictly to `127.0.0.1`. Inbound Windows Firewall rules are never requested or required.
- **Data Protection**: Firewall telemetry, hostnames, IP addresses, serial numbers, and screenshots are never transmitted externally.
- **Licensing**:
  - `llama.cpp`: MIT License (Release b11200).
  - `Qwen 2.5 / Qwen 3`: Apache 2.0 License.
  - LLVM OpenMP runtime (`libomp.dll`): Apache 2.0 License with LLVM Exceptions.
  - Complete attribution notices are documented in `THIRD_PARTY_LICENSES.txt`.

