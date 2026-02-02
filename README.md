# File Descriptor Forensics and Code Sandbox

A Linux-only tool for live process file descriptor (FD) forensics and sandboxed code execution with FD tracking. It combines read-only `/proc` inspection with optional Gemini AI–based forensic summarization and PDF report generation.

---

## Overview

This project does the following today:

- **Live Linux process FD analysis via /proc** — Lists all processes with FD counts (from `/proc/{pid}/fd`), and for any selected process provides a full FD analysis: per-FD table (FD number, target path or kernel object, type), type counts, severity, and textual interpretation. Process list is sorted by FD count descending. The UI also shows a system overview: Top 5 FD-heavy and Bottom 5 FD-light processes (overview is UI-only; not included in PDF reports).

- **Secure sandboxed execution of uploaded Python and C programs** — Users upload a single `.py` or `.c` file. Python files are executed with `python3` in a subprocess; C files are compiled with `gcc` and the resulting binary is executed. Execution runs in a new process group with a configurable timeout (default 30 seconds) and a per-process FD limit (default 256) enforced via `RLIMIT_NOFILE`. On timeout, the process group is terminated with `SIGKILL`. There is no network sandboxing; only time and FD limits are applied.

- **Real-time FD growth tracking during execution** — A background thread samples the child process’s open FD count (and optionally the full FD snapshot) at a fixed interval (0.1 seconds) by reading `/proc/{pid}/fd`. Samples are stored as (time_sec, fd_count) and normalized so that time starts at 0 for the first sample. This time series is the source of the FD growth line chart in the Code Analysis UI and of the “FD growth” summary in the code analysis PDF.

- **FD classification (Standard, File, Pipe, Socket, Other)** — Each FD is classified using Linux semantics: FDs 0, 1, 2 are always “Standard”; targets starting with `socket:` → “Socket”, `pipe:` → “Pipe”, path starting with `/` → “File”; everything else → “Other”. Classification is used for type counts, risk explanation, and the FD type pie/donut chart in both Live Process and Code Analysis views.

- **Severity and risk analysis based on FD behavior** — For live process and code-run snapshots, the backend computes: total FD count, non-standard count, FD density (non-standard/total), and usage percentage vs. soft limit when available. Severity is derived from rules (e.g. CRITICAL when usage ≥ 90% of limit, HIGH at 70–90%, MEDIUM when total FDs ≥ 200, otherwise LOW). Textual “forensic interpretation” and per-type risk explanations are included in the API response and PDFs.

- **Optional Gemini AI–based forensic summary** — When a Gemini API key is configured (via `.env` or the Code Analysis UI), the code execution report (metadata, FD growth, FD snapshot analysis) is sent to Google Gemini. The model returns a structured forensic summary (FD summary, risk assessment, evidence, recommendations). If the key is missing or invalid, the app returns a fallback message and does not fail; AI is optional and fail-safe.

- **Timestamped snapshots of analysis** — Process analysis responses include a `snapshot_taken_at` UTC timestamp. Code execution reports include `sampling_started_at` and `snapshot_taken_at` (UTC) for reproducibility.

- **PDF report generation** — Implemented and available: (1) Live process analysis PDF: `GET /process/{pid}/analysis/pdf` returns a PDF with metrics, severity, interpretation, FD type breakdown (with pie chart), and FD table. (2) Code analysis PDF: `POST /analyze/code/pdf` runs the same sandboxed execution and analysis, then returns a PDF that includes execution metadata, stdout/stderr, FD growth summary, FD analysis table (and optional pie chart), and the AI forensic summary when available.

---

## Architecture

- **Frontend:** React 18 with React Router 6, built with Vite 5. Uses Axios for API calls and Recharts for the FD type pie chart (Live Processes) and FD growth line chart (Code Analysis). Two main routes: Live Processes (process list, FD overview, per-process analysis, PDF download) and Code Analysis (file upload, execution metadata, FD growth chart, FD table, AI summary, PDF download).

- **Backend:** FastAPI application (`backend.api:app`) served with Uvicorn. Exposes REST endpoints for process listing, per-process FD analysis, process analysis PDF, code analysis (JSON), and code analysis PDF. Loads environment from `.env` (e.g. `GEMINI_API_KEY`). CORS is enabled for all origins. No database; stateless.

- **OS interface:** Linux `/proc` filesystem only. Process list from `/proc` directory and per-process `comm`, `status`, `limits`, and `fd` (readlink). No ptrace; observation only for live processes.

- **Execution sandbox:** Implemented in `backend/analyzer/code_executor.py`. Uses `subprocess.Popen` with `start_new_session=True`, `preexec_fn` to set `resource.RLIMIT_NOFILE(soft, hard)` before exec, and a daemon thread that samples `/proc/{pid}/fd` at a fixed interval. On timeout, `os.killpg(os.getpgid(pid), signal.SIGKILL)` is used. No network or filesystem isolation beyond FD limit and timeout.

- **AI integration:** Optional Google Gemini API via `backend/ai/gemini_client.py`. API key can be provided in `.env` as `GEMINI_API_KEY` or in the Code Analysis form. The client builds a structured prompt from the execution report and requests a short forensic summary. Multiple model names are tried on 404. Errors (invalid key, quota, blocked, network) are classified and returned as user-safe messages; API keys are never echoed. If no key is set, the app does not call Gemini and returns a fallback message.

---

## Supported Languages

| Language | Extension | Execution |
|----------|------------|-----------|
| **Python** | `.py` | Run with `python3` in the sandbox (no compile step). |
| **C** | `.c` | Compiled with `gcc` (e.g. `gcc source.c -o program`) in the source directory; the resulting binary is then executed in the same sandbox (timeout, FD limit, FD sampling). Compile errors are returned in the execution report; no binary is run. |

Only single-file uploads are supported. Files must be UTF-8 encoded.

---

## How FD Tracking Works

- **Sampling frequency:** During sandboxed execution, a background thread reads the child process’s FD count (and full FD list for the final snapshot) every **0.1 seconds** (`FD_SAMPLE_INTERVAL_SEC` in `code_executor.py`). Sampling continues until the process exits or the main thread stops it after timeout/kill.

- **Snapshot timing:** For **live process analysis**, the FD list and limits are read at the time of the HTTP request; the response includes a single `snapshot_taken_at` (UTC). For **code execution**, sampling starts when the process starts; the last sample before the process exits (or before the sampler is stopped) is used as the “FD snapshot” for the FD analysis table and type breakdown. Timestamps `sampling_started_at` and `snapshot_taken_at` (UTC) are stored in the execution metadata.

- **How FD growth graphs are derived:** The raw samples are (monotonic time_sec, fd_count). They are normalized so that the first sample has time_sec 0; this normalized list is `fd_growth` in the API. The frontend FD growth line chart plots `fd_growth` as time_sec (x-axis) vs fd_count (y-axis). The same data is summarized in the code analysis PDF (e.g. sample count, time range, max FD count).

---

## How to Run

### Prerequisites

- **Linux** (required; uses `/proc` and `RLIMIT_NOFILE`).
- **Python 3.9+** for the backend.
- **Node.js 18+** and npm for the frontend.
- **gcc** for C file compilation (Code Analysis).

### Environment setup

- Copy `.env.example` to `.env` in the project root if you want to use AI summarization. Set `GEMINI_API_KEY` in `.env` (see `.env.example`). Do not commit `.env` or any secrets; `.env` is listed in `.gitignore`.
- No other environment variables are required for basic operation.

### One-command run (recommended)

From the project root:

```bash
cd /home/sashank/fd-forensics-copy
./run.sh
```

This script:

- Finds free ports for backend (tries 8000–8004) and frontend (tries 5173–5176).
- Creates `.env` from `.env.example` if `.env` does not exist.
- Loads `.env` and installs backend dependencies (`pip install -r backend/requirements.txt`).
- Starts the backend with: `uvicorn backend.api:app --host 0.0.0.0 --port <BACKEND_PORT>`.
- After a short delay, starts the frontend with `VITE_API_BASE_URL=http://localhost:<BACKEND_PORT>` and `npm run dev -- --port <FRONTEND_PORT>`.
- Attempts to open the app in the browser at `http://localhost:<FRONTEND_PORT>`.

### Manual run (two terminals)

**Backend:**

```bash
cd /home/sashank/fd-forensics-copy
[ -f .env ] && set -a && . ./.env && set +a
pip install -r backend/requirements.txt
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd /home/sashank/fd-forensics-copy/frontend
npm install
npm run dev
```

Then open http://localhost:5173 (or the port Vite prints). If the backend runs on a different port, set `VITE_API_BASE_URL=http://localhost:<port>` when starting the frontend so it can reach the API.

---

## Security and Limitations

- **Linux-only:** Relies on `/proc` and `RLIMIT_NOFILE`; not supported on Windows or macOS.
- **No network sandboxing:** Sandboxed code can use the network; only time and FD limits are enforced.
- **Time and FD limits:** Default 30 s timeout and FD limit 256; reduces impact of runaway or FD-leaking programs but does not isolate network or filesystem.
- **AI summaries are advisory, not authoritative:** Gemini output is for guidance only; it is not a substitute for manual review or security guarantees.

---

## Current Limitations

- **No historical persistence:** No database; process list and analysis are point-in-time. Code analysis runs are not stored; only the last result is shown in the UI.
- **Single-file uploads:** One `.py` or `.c` file per analysis; no multi-file or project support.
- **No Windows/macOS support:** Requires Linux and `/proc`.
- **Read-only /proc:** No ptrace or control of other processes; observation only for live process analysis.
- **Single execution per upload:** Each upload triggers one run; no built-in session or run history.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/processes` | List all processes with `pid`, `name`, `user`, `fd_count` (sorted by `fd_count` descending). |
| GET | `/process/{pid}/analysis` | Full FD analysis for the given process (table, type counts, severity, interpretation, timestamps). |
| GET | `/process/{pid}/analysis/pdf` | Same analysis as PDF download. |
| POST | `/analyze/code` | Upload a `.py` or `.c` file; execute in sandbox; return JSON (raw analysis + AI summary or fallback message). Optional form field: `gemini_api_key`. |
| POST | `/analyze/code/pdf` | Same as `/analyze/code` but response is `application/pdf`. Optional form field: `gemini_api_key`. |

---

## Project Structure

```
├── proc/                    # Read /proc (process list, FD list, limits)
│   ├── fd_reader.py
│   ├── process_info.py
│   └── process_list.py
├── analysis/                # FD classification and report building
│   ├── fd_classifier.py
│   └── report_builder.py
├── backend/
│   ├── api.py               # FastAPI app and endpoints
│   ├── analyzer/
│   │   └── code_executor.py # Sandbox: compile_c, execute_code_safely, execute_binary_safely
│   ├── ai/
│   │   └── gemini_client.py # Gemini summarization
│   ├── pdf_report.py        # Process and code analysis PDF generation
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # fdForensicsApi.js
│   │   ├── components/      # ProcessList, ProcessAnalysis, CodeUpload, FDGrowthChart, FDTypePieChart, AISummary
│   │   ├── pages/           # LiveProcesses, CodeAnalysis
│   │   ├── App.jsx, main.jsx, index.css, App.css
│   │   └── ...
│   ├── index.html
│   ├── package.json
│   └── vite.config.js       # Proxy for /processes, /process, /analyze
├── app.py                   # Optional Streamlit UI (same proc/analysis logic; separate from main app)
├── run.sh                   # One-command backend + frontend startup
├── .env.example             # Example env (GEMINI_API_KEY only)
├── .gitignore
└── README.md
```

---

## Environment

- **GEMINI_API_KEY** (optional): Set in `.env` (or pass via Code Analysis form) to enable AI forensic summaries. Copy `.env.example` to `.env` and set the value; do not commit `.env` or any API keys.
