# File Descriptor Forensics and Code Sandbox

A Linux file descriptor forensics tool for live process analysis and safe code execution with FD tracking. Combines OS-level `/proc` inspection with AI-powered summarization (Gemini, optional).

---

## What It Does

- **Live process analysis** — Inspect any running process's open FDs, classify by type (Standard, File, Pipe, Socket, Other), assess severity, view FD type pie chart and breakdown.
- **Code sandbox** — Upload Python (`.py`) or C (`.c`) files; execute in a subprocess with timeout and FD limits; capture FD growth over time; produce forensic report.
- **FD graphs** — Donut chart for FD type distribution (Live Processes); line chart for FD count over time (Code Analysis).
- **Timestamps** — Snapshot timestamps (UTC) for process analysis and code execution.
- **AI summarization** — Send the report to Google Gemini for leak detection, root cause, severity, and fix recommendations. Requires `GEMINI_API_KEY`; falls back to a message if disabled.
- **PDF export** — Download PDF reports for live process analysis and code analysis runs.
- **System overview** — Top 5 FD-heavy and Bottom 5 FD-light processes (UI only; not in PDF).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React Frontend (Vite)                                           │
│  - Live Processes: process list, FD overview, FD analysis,       │
│    pie chart, metrics, Download PDF                              │
│  - Code Analysis: upload, execution report, FD growth chart,     │
│    FD table, AI summary, Download PDF                            │
└─────────────────────────────────────────────────────────────────┘
                                    │ HTTP / JSON
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                                 │
│  GET /processes, GET /process/{pid}/analysis,                    │
│  GET /process/{pid}/analysis/pdf                                 │
│  POST /analyze/code, POST /analyze/code/pdf                      │
└─────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐  ┌─────────────────────────┐  ┌─────────────────────┐
│ proc/           │  │ backend/analyzer/       │  │ backend/ai/         │
│ (read /proc)    │  │ code_executor.py        │  │ gemini_client.py    │
│                 │  │ compile_c, execute_*    │  └─────────────────────┘
└─────────────────┘  └─────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐  ┌─────────────────────────┐
│ analysis/       │  │ subprocess + RLIMIT,    │
│ fd_classifier   │  │ FD sampling, timeout,   │
│ report_builder  │  │ killpg on timeout       │
└─────────────────┘  └─────────────────────────┘
```

---

## Supported Languages and Limitations

| Supported           | Details                                                      |
|---------------------|--------------------------------------------------------------|
| **Python**          | `.py` files executed via `python3`                           |
| **C**               | `.c` files compiled with `gcc`, then binary executed         |

| Limitation          | Reason                                                       |
|---------------------|--------------------------------------------------------------|
| **Linux only**      | Uses `/proc` and `RLIMIT_NOFILE`                             |
| **Read-only /proc** | No ptrace; observation only for live processes               |
| **Single execution**| Each upload runs once; no sessions                           |
| **Gemini optional** | AI summarization requires `GEMINI_API_KEY`; core analysis works without it |

---

## How to Run

### Prerequisites

- Linux
- Python 3.9+
- Node.js 18+
- (Optional) `GEMINI_API_KEY` in `.env` for AI summarization

### One Command (Recommended)

```bash
cd /path/to/fd-forensics-copy
./run.sh
```

This will:
- Pick free ports if 8000/5173 are in use
- Start backend and frontend
- Open the app in your browser

### Manual (Two Terminals)

**Backend:**
```bash
cd /path/to/fd-forensics-copy
[ -f .env ] && set -a && . ./.env && set +a
pip install -r backend/requirements.txt
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (or the port Vite reports).

---

## Project Structure

```
├── proc/                 # OS-facing: read /proc (DO NOT MODIFY)
│   ├── fd_reader.py
│   ├── process_info.py
│   └── process_list.py
├── analysis/             # FD classification and severity (fd_classifier: DO NOT MODIFY)
│   ├── fd_classifier.py
│   └── report_builder.py
├── backend/
│   ├── api.py
│   ├── analyzer/code_executor.py
│   ├── ai/gemini_client.py
│   ├── pdf_report.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   └── vite.config.js
├── run.sh
├── .env.example
└── README.md
```

---

## API Endpoints

| Method | Endpoint                   | Description                         |
|--------|----------------------------|-------------------------------------|
| GET    | /processes                 | List processes with FD counts       |
| GET    | /process/{pid}/analysis    | FD analysis for a process           |
| GET    | /process/{pid}/analysis/pdf| PDF report for process analysis     |
| POST   | /analyze/code              | Upload .py/.c, run, return JSON     |
| POST   | /analyze/code/pdf          | Upload .py/.c, run, return PDF      |

---

## Environment

- `GEMINI_API_KEY` — Optional. Enables AI summarization; copy from `.env.example` to `.env` and set the value.
- `.env` is gitignored; never commit secrets.
