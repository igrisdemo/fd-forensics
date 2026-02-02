# File Descriptor Forensics and Code Sandbox

A Linux file descriptor forensics tool for live process analysis and safe code execution with FD tracking. Combines OS-level `/proc` inspection with AI-powered summarization.

---

## Project Overview

**Problem:** File descriptor (FD) leaks are a common cause of production outages. Processes that open files, sockets, or pipes without closing them eventually hit the per-process FD limit, leading to "Too many open files" errors and service failures. Detecting and diagnosing FD leaks is difficult without intrusive instrumentation.

**Solution:** File Descriptor Forensics and Code Sandbox provides:

1. **Live process analysis** — Inspect any running process's open FDs, classify them by type (Standard, File, Pipe, Socket, Other), and assess severity.
2. **Code analysis** — Execute uploaded Python code in a sandbox with FD limits, capture FD growth over time, and produce a forensic report.
3. **AI summarization** — Send the report to Google Gemini for human-readable analysis, leak detection, and fix recommendations.

---

## Why FD Leaks Matter

From a systems and security perspective:

- **Resource exhaustion:** Each FD consumes kernel memory. Leaked FDs accumulate until `ulimit` is reached.
- **Denial of service:** A single misbehaving process can exhaust FDs and block sibling processes or the whole system.
- **Sockets and pipes are worse:** They hold buffers, connection state, and IPC resources. Leaked sockets block ports and memory longer than regular files.
- **Forensic value:** FD types and counts reveal what a process is doing—file I/O, network, IPC—without attaching debuggers.

The tool ranks FD types by risk: Standard (low) → File → Pipe → Other → Socket (high).

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React Frontend (Vite)                                           │
│  - Live Processes page (process list + FD analysis)              │
│  - Code Analysis page (upload, execution report, AI summary)     │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP / JSON
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                                 │
│  - GET /processes, GET /process/{pid}/analysis                   │
│  - POST /analyze/code (upload → execute → analyze → Gemini)      │
└─────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│ proc/            │  │ backend/analyzer/    │  │ backend/ai/      │
│ (read /proc)     │  │ code_executor.py     │  │ gemini_client.py │
└──────────────────┘  └──────────────────────┘  └──────────────────┘
              │                     │
              ▼                     ▼
┌──────────────────┐  ┌──────────────────────┐
│ analysis/        │  │ subprocess + RLIMIT  │
│ (classify,       │  │ FD sampling thread   │
│  severity)       │  │ timeout, killpg      │
└──────────────────┘  └──────────────────────┘
```

---

## Feature List

| Feature | Description |
|---------|-------------|
| **Live Process List** | All processes with FD counts, sorted by FD usage. |
| **Per-Process FD Analysis** | FD table, type breakdown, severity (LOW/MEDIUM/HIGH/CRITICAL), usage vs soft limit, forensic interpretation. |
| **Code Upload & Execution** | Upload `.py` file; execute in subprocess with timeout and `RLIMIT_NOFILE`. |
| **FD Growth Chart** | Time-series of FD count during execution (samples every 100ms). |
| **Execution Metadata** | PID, duration, termination reason (normal/error/timeout), exit code, stdout/stderr. |
| **AI Summary** | Gemini analysis: FD leaks detected, root cause, severity, fix recommendations. Fallback message when Gemini is unavailable. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, uvicorn |
| Frontend | React 18, Vite, React Router, Axios, Recharts |
| AI | Google Generative AI (Gemini) |
| OS | Linux `/proc` filesystem |

---

## How to Run

### Prerequisites

- Linux (uses `/proc`)
- Python 3.9+
- Node.js 18+
- (Optional) `GEMINI_API_KEY` for AI summarization

### Backend

```bash
cd /path/to/fd-forensics-copy
pip install -r backend/requirements.txt
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/processes`, `/process`, and `/analyze` to the backend.

### Production

Build frontend: `npm run build` in `frontend/`. Serve `frontend/dist/` and reverse-proxy API requests to the backend.

---

## Example Workflows

### 1. Live Process Analysis

1. Open the app → "Live Processes" (default).
2. Processes load; list is sorted by FD count (highest first).
3. Click a PID (e.g. a browser or IDE).
4. View metrics, severity, FD type breakdown, and FD table.

### 2. Code Analysis with FD Tracking

1. Go to "Code Analysis".
2. Upload a Python file (e.g. one that opens files in a loop).
3. Wait for execution (timeout 30s, FD limit 256).
4. Inspect execution metadata, FD growth chart, FD table, and AI summary.

### 3. API Usage

```bash
# List processes
curl http://localhost:8000/processes

# Per-process analysis
curl http://localhost:8000/process/1234/analysis

# Code analysis
curl -X POST -F "file=@script.py" http://localhost:8000/analyze/code
```

---

## Limitations and Assumptions

| Limitation | Reason |
|------------|--------|
| **Linux only** | Relies on `/proc` and `RLIMIT_NOFILE`; not available on Windows/macOS. |
| **Python code execution only** | Sandbox currently executes `.py` files via `python3`. |
| **Read-only /proc** | No process injection or ptrace; observation only for live processes. |
| **Single execution** | Each upload runs once; no persistent sessions. |
| **Gemini optional** | AI summarization requires `GEMINI_API_KEY`; core analysis works without it. |

---

## Future Scope

Realistic, non-invasive extensions:

- Support for other languages (e.g. shell scripts, binaries with configurable args).
- Historical FD snapshots (store samples for later comparison).
- Export reports (JSON, PDF).
- Configurable timeout and FD limit per request.
- LD_PRELOAD-based FD interception (opt-in, for deeper analysis).

---

## Architecture Explanation

### Why /proc Is Used

The Linux `/proc` filesystem exposes kernel and process state as files. For each process `pid`:

- `/proc/{pid}/fd` — directory of open FD numbers (symlinks to targets)
- `/proc/{pid}/fd/{n}` — `readlink` gives target: `socket:[...]`, `pipe:[...]`, or path
- `/proc/{pid}/limits` — `Max open files` (soft, hard)
- `/proc/{pid}/comm` — process name
- `/proc/{pid}/status` — UID and other metadata

This is the standard, non-invasive way to inspect process FDs. No debuggers or kernel modules.

### Why Core OS Modules Are Frozen

The modules `proc/` and `analysis/fd_classifier.py` implement the contract with the Linux kernel and FD semantics. Changing them risks:

- Misreading `/proc` formats (which can vary across kernel versions)
- Breaking FD classification rules (e.g. fd 0/1/2 semantics)
- Incorrect severity logic

They are treated as stable, tested boundaries. New features go in `backend/` or `frontend/`.

### Why FastAPI + React Separation

- **API-first:** The backend is a pure REST API. Any client (web, CLI, mobile) can consume it.
- **Clear contract:** Pydantic schemas define request/response shapes. Frontend and backend evolve independently.
- **CORS-friendly:** React dev server and production builds call the API cleanly.
- **Testability:** API can be tested without a browser.

### Why AI Summarization Is Optional and Safe

- **Optional:** If `GEMINI_API_KEY` is unset or invalid, the API returns a fallback message. The full `raw_analysis` (execution metadata, FD growth, FD table) is always returned.
- **Safe:** Gemini is called only after local execution and analysis. No code or sensitive data is sent beyond the structured report. Failures are caught; the endpoint never crashes.

---

## Demo Script

### Setup (before demo)

```bash
# Terminal 1
uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173.

### Part 1: Live Processes (≈2 min)

1. **Landing page** — "Live Processes" shows a list of processes by FD count.
2. **Select a process** — Click a high-FD process (e.g. browser, IDE).
3. **Explain metrics** — Total FDs, non-standard count, FD density, usage vs limit, severity.
4. **Explain severity** — LOW (controlled), MEDIUM (≥200 FDs), HIGH (70–90% of limit), CRITICAL (≥90%).
5. **Show FD table** — FD number, target (socket/pipe/path), type.

### Part 2: Code Analysis (≈3 min)

1. Go to **Code Analysis**.
2. **Prepare a script** — e.g. `test.py`:
   ```python
   f = open("/dev/null")
   import time; time.sleep(1)
   f.close()
   print("done")
   ```
3. **Upload** — Drag-and-drop or click to choose.
4. **Show execution metadata** — PID, duration, termination (normal), FD limit.
5. **Show FD growth chart** — Line chart: FD count over time.
6. **Show FD analysis** — Table with Standard (0,1,2), File (3 = /dev/null).
7. **Show AI summary** — If `GEMINI_API_KEY` is set: sections on leaks, root cause, severity, recommendations. If not: fallback message.

### Part 3: Edge Cases (≈1 min)

- **Backend down** — Stop uvicorn; refresh. Error banner and "Backend unavailable" message.
- **Non-.py upload** — Try uploading a `.txt` file. Inline error: "Only .py files are accepted."
- **Timeout** — Upload a script with `while True: pass`. Termination = timeout; process killed.

### Key Talking Points

- **Severity:** Based on FD count and usage percentage. High FD count alone does not mean leak; it increases impact if descriptors are not released.
- **FD growth:** A steadily increasing line suggests possible leak; flat line is normal.
- **Type risk:** Sockets and pipes carry more kernel state than regular files; leaks are more severe.

---

## Viva / Review Q&A

### FD Tracking

**Q: How are file descriptors tracked?**  
A: Via `/proc/{pid}/fd`. Each entry is a symlink; `readlink` returns the target (e.g. `socket:[12345]`, `pipe:[12346]`, `/path/to/file`). The directory length is the FD count.

**Q: Why sample FD count during execution instead of only at the end?**  
A: After a process exits, `/proc/{pid}` is gone. Sampling every 100ms while the process runs captures growth over time and a final snapshot before exit.

### ulimit and RLIMIT_NOFILE

**Q: Why set RLIMIT_NOFILE in the sandbox?**  
A: To bound resource use and simulate a constrained environment. It also triggers "Too many open files" when a script leaks FDs, which we detect via stderr.

**Q: How is it applied?**  
A: Using `resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))` in `preexec_fn` of `subprocess.Popen`. This runs in the child before `exec`, so the limit applies to the executed process.

### Zombie Prevention

**Q: How are zombie processes prevented on timeout?**  
A: The executor uses `start_new_session=True` so the child has its own process group. On timeout, we call `os.killpg(os.getpgid(pid), signal.SIGKILL)` to kill the whole group, then `proc.wait()` to reap the process. No orphaned children.

**Q: What if the child spawns grandchildren?**  
A: Killing the process group terminates all descendants. Session isolation keeps them from leaking back to the parent.

### Gemini Failures

**Q: What happens if Gemini fails or API key is missing?**  
A: `summarize_fd_report` returns `None` on any failure. The API catches this and sets `ai_summary` to a fallback string. The endpoint always returns 200 with full `raw_analysis`; only the AI section changes.

**Q: Does a Gemini failure affect execution or FD analysis?**  
A: No. Execution and FD analysis run first. Gemini is called last, and its result is optional.

---

## Project Structure

```
fd-forensics-copy/
├── proc/                 # OS-facing: read /proc (DO NOT MODIFY)
│   ├── fd_reader.py
│   ├── process_info.py
│   └── process_list.py
├── analysis/             # FD classification and severity (fd_classifier: DO NOT MODIFY)
│   ├── fd_classifier.py
│   └── report_builder.py
├── backend/              # FastAPI API and services
│   ├── api.py
│   ├── analyzer/code_executor.py
│   ├── ai/gemini_client.py
│   └── requirements.txt
├── frontend/             # React UI
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   ├── package.json
│   └── vite.config.js
└── README.md
```
