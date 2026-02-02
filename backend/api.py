"""
FastAPI backend for FD Forensics.
Exposes REST endpoints for process listing, FD analysis, and code execution analysis.
"""

import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

# Ensure project root is on path for proc/ and analysis/ imports
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from proc.process_list import list_processes
from proc.fd_reader import read_fds
from proc.process_info import get_fd_limits
from analysis.report_builder import analyze_fds

from backend.analyzer.code_executor import (
    execute_code_safely,
    execute_binary_safely,
    compile_c,
)
from backend.ai.gemini_client import summarize_fd_report
from backend.pdf_report import generate_process_pdf, generate_code_pdf

logger = logging.getLogger(__name__)

# -----------------------------
# APP
# -----------------------------
app = FastAPI(
    title="FD Forensics API",
    description="Linux file descriptor forensics and code execution analysis",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# -----------------------------
# RESPONSE SCHEMAS
# -----------------------------
class ProcessItem(BaseModel):
    pid: int
    name: str
    user: str
    fd_count: int


class FDEntry(BaseModel):
    FD: int
    Target: str
    Type: str


class ProcessAnalysisResponse(BaseModel):
    table: list[FDEntry]
    type_counts: dict[str, int]
    non_standard: int
    severity: str
    severity_reason: str
    severity_condition: str
    analysis: list[str]
    usage_pct: Optional[float]
    fd_density: float
    fd_danger_rank: dict[str, int]
    fd_danger_reason: dict[str, str]


class ExecutionMeta(BaseModel):
    pid: Optional[int]
    duration_seconds: Optional[float]
    termination_reason: str
    exit_code: Optional[int]
    stdout: str = ""
    stderr: str = ""
    timeout_sec: Optional[int]
    fd_limit: Optional[int]
    language: str = "python"


class FDAnalysisSummary(BaseModel):
    table: list[dict[str, Any]]
    type_counts: dict[str, int]
    non_standard: int
    severity: str
    severity_reason: str
    usage_pct: Optional[float]
    fd_density: float


class RawAnalysis(BaseModel):
    execution: ExecutionMeta
    fd_growth: list[dict[str, Any]]
    fd_analysis: Optional[FDAnalysisSummary] = None


class CodeAnalysisResponse(BaseModel):
    raw_analysis: RawAnalysis
    ai_summary: str = Field(..., description="Human-readable AI summary or fallback message")


class ErrorDetail(BaseModel):
    detail: str
    error: str = "error"


# -----------------------------
# EXCEPTION HANDLER
# -----------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Ensure HTTP exceptions return consistent JSON structure."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error": "error"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """Catch unhandled exceptions and return structured JSON."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": "error"},
    )


# -----------------------------
# ENDPOINTS
# -----------------------------


@app.get("/processes", response_model=list[ProcessItem])
def get_processes():
    """
    List all processes with FD counts, sorted by fd_count descending.
    """
    processes = list_processes()
    return [ProcessItem(**p) for p in processes]


@app.get("/process/{pid}/analysis", response_model=ProcessAnalysisResponse)
def get_process_analysis(pid: int):
    """
    Full FD analysis for a given process: FD table, type counts, severity, etc.
    """
    try:
        fds = read_fds(pid)
        soft, _hard = get_fd_limits(pid)
        soft_limit = int(soft) if soft.isdigit() else None
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Process {pid} not found or inaccessible: {str(e)}",
        )

    result = analyze_fds(fds, soft_limit)

    return ProcessAnalysisResponse(
        table=[FDEntry(**r) for r in result["table"]],
        type_counts=dict(result["type_counts"]),
        non_standard=result["non_standard"],
        severity=result["severity"],
        severity_reason=result["severity_reason"],
        severity_condition=result["severity_condition"],
        analysis=result["analysis"],
        usage_pct=result["usage_pct"],
        fd_density=result["fd_density"],
        fd_danger_rank=result["fd_danger_rank"],
        fd_danger_reason=result["fd_danger_reason"],
    )


@app.get("/process/{pid}/analysis/pdf")
def get_process_analysis_pdf(pid: int):
    """
    Generate and download PDF report for process FD analysis.
    Reuses same analysis data as GET /process/{pid}/analysis.
    """
    try:
        fds = read_fds(pid)
        soft, _hard = get_fd_limits(pid)
        soft_limit = int(soft) if soft.isdigit() else None
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Process {pid} not found or inaccessible: {str(e)}",
        )

    result = analyze_fds(fds, soft_limit)
    data = {
        "table": result["table"],
        "type_counts": dict(result["type_counts"]),
        "non_standard": result["non_standard"],
        "severity": result["severity"],
        "severity_reason": result["severity_reason"],
        "severity_condition": result["severity_condition"],
        "analysis": result["analysis"],
        "usage_pct": result["usage_pct"],
        "fd_density": result["fd_density"],
        "fd_danger_rank": result["fd_danger_rank"],
        "fd_danger_reason": result["fd_danger_reason"],
    }

    pdf_bytes = generate_process_pdf(pid, data)
    filename = f"fd-forensics-process-{pid}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/analyze/code", response_model=CodeAnalysisResponse)
async def analyze_code(file: UploadFile = File(...)):
    """
    Upload a Python or C file, execute it safely with FD tracking, analyze FD behavior,
    and return raw analysis plus AI summary from Gemini.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = file.filename.lower().endswith
    if not (ext(".py") or ext(".c")):
        raise HTTPException(status_code=400, detail="Only .py and .c files are accepted")

    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    is_python = file.filename.lower().endswith(".py")
    language = "python" if is_python else "c"

    if is_python:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(decoded)
            tmp_path = f.name
        tmp_dir = None
        binary_path = None
    else:
        tmp_dir = tempfile.mkdtemp()
        source_path = os.path.join(tmp_dir, "main.c")
        with open(source_path, "w") as f:
            f.write(decoded)
        tmp_path = source_path
        binary_path = os.path.join(tmp_dir, "program")

    try:
        if is_python:
            exec_report = execute_code_safely(tmp_path)
            exec_report["language"] = "python"
        else:
            success, compile_stdout, compile_stderr, out_binary = compile_c(tmp_path, "program")
            if not success:
                exec_report = {
                    "pid": None,
                    "duration_seconds": 0.0,
                    "termination_reason": "compile_error",
                    "exit_code": None,
                    "stdout": compile_stdout,
                    "stderr": compile_stderr,
                    "fd_samples": [],
                    "fd_snapshot": [],
                    "timeout_sec": 30,
                    "fd_limit": 256,
                }
                exec_report["language"] = "c"
            else:
                exec_report = execute_binary_safely(out_binary)
                exec_report["language"] = "c"

        raw_analysis = _build_raw_analysis(exec_report)

        ai_summary: str
        try:
            ai_summary = summarize_fd_report(raw_analysis) or (
                "AI summarization unavailable. Set GEMINI_API_KEY environment variable."
            )
        except Exception as e:
            logger.warning("Gemini summarization failed: %s", e)
            ai_summary = (
                "AI summarization unavailable. Set GEMINI_API_KEY environment variable."
            )

        return CodeAnalysisResponse(
            raw_analysis=RawAnalysis(**raw_analysis),
            ai_summary=ai_summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Code analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_python:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        else:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except OSError:
                pass


@app.post("/analyze/code/pdf")
async def analyze_code_pdf(file: UploadFile = File(...)):
    """
    Upload a Python or C file, run analysis, and return PDF report.
    Same execution and analysis as POST /analyze/code, but returns application/pdf.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = file.filename.lower().endswith
    if not (ext(".py") or ext(".c")):
        raise HTTPException(status_code=400, detail="Only .py and .c files are accepted")

    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    is_python = file.filename.lower().endswith(".py")

    if is_python:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(decoded)
            tmp_path = f.name
        tmp_dir = None
    else:
        tmp_dir = tempfile.mkdtemp()
        source_path = os.path.join(tmp_dir, "main.c")
        with open(source_path, "w") as f:
            f.write(decoded)
        tmp_path = source_path

    try:
        if is_python:
            exec_report = execute_code_safely(tmp_path)
            exec_report["language"] = "python"
        else:
            success, compile_stdout, compile_stderr, out_binary = compile_c(tmp_path, "program")
            if not success:
                exec_report = {
                    "pid": None,
                    "duration_seconds": 0.0,
                    "termination_reason": "compile_error",
                    "exit_code": None,
                    "stdout": compile_stdout,
                    "stderr": compile_stderr,
                    "fd_samples": [],
                    "fd_snapshot": [],
                    "timeout_sec": 30,
                    "fd_limit": 256,
                }
                exec_report["language"] = "c"
            else:
                exec_report = execute_binary_safely(out_binary)
                exec_report["language"] = "c"

        raw_analysis = _build_raw_analysis(exec_report)

        ai_summary: str
        try:
            ai_summary = summarize_fd_report(raw_analysis) or (
                "AI summarization unavailable. Set GEMINI_API_KEY environment variable."
            )
        except Exception as e:
            logger.warning("Gemini summarization failed: %s", e)
            ai_summary = (
                "AI summarization unavailable. Set GEMINI_API_KEY environment variable."
            )

        pdf_bytes = generate_code_pdf(raw_analysis, ai_summary)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"fd-forensics-code-{ts}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Code analysis PDF failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_python:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        else:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except OSError:
                pass


def _build_raw_analysis(exec_report: dict) -> dict:
    """
    Build the structured FD execution report for API response and Gemini.
    Uses fd_snapshot captured during execution (process may have exited).
    """
    out = {
        "execution": {
            "pid": exec_report.get("pid"),
            "duration_seconds": exec_report.get("duration_seconds"),
            "termination_reason": exec_report.get("termination_reason"),
            "exit_code": exec_report.get("exit_code"),
            "stdout": exec_report.get("stdout", ""),
            "stderr": exec_report.get("stderr", ""),
            "timeout_sec": exec_report.get("timeout_sec"),
            "fd_limit": exec_report.get("fd_limit"),
            "language": exec_report.get("language", "python"),
        },
        "fd_growth": exec_report.get("fd_samples", []),
        "fd_analysis": None,
    }

    fd_snapshot = exec_report.get("fd_snapshot", [])
    if fd_snapshot:
        fd_limit = exec_report.get("fd_limit")
        soft_limit = int(fd_limit) if fd_limit is not None else None
        analysis = analyze_fds(fd_snapshot, soft_limit)
        out["fd_analysis"] = {
            "table": analysis["table"],
            "type_counts": dict(analysis["type_counts"]),
            "non_standard": analysis["non_standard"],
            "severity": analysis["severity"],
            "severity_reason": analysis["severity_reason"],
            "usage_pct": analysis["usage_pct"],
            "fd_density": analysis["fd_density"],
        }

    return out
