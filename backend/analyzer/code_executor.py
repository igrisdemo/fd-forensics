"""
Safe code execution with FD tracking.
Executes a Python file in a subprocess with timeout and RLIMIT_NOFILE.
Samples FD count over time and captures final FD snapshot.
"""

import logging
import os
import resource
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Default execution constraints
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_FD_LIMIT = 256
FD_SAMPLE_INTERVAL_SEC = 0.1
FD_LIMIT_VIOLATION_INDICATORS = ("too many open files", "emfile", "errno 24")


def _count_fds(pid: int) -> int:
    """Return number of open FDs for a process."""
    try:
        return len(os.listdir(f"/proc/{pid}/fd"))
    except (FileNotFoundError, PermissionError):
        return -1


def _read_fds(pid: int) -> list[dict]:
    """Read FD entries for a process. Returns list of {fd, target}."""
    entries = []
    path = f"/proc/{pid}/fd"
    try:
        for fd in os.listdir(path):
            target = os.readlink(f"{path}/{fd}")
            entries.append({"fd": int(fd), "target": target})
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return entries


def _fd_sampler(
    pid: int,
    fd_samples: list,
    last_fd_snapshot: dict,
    stop_event: threading.Event,
) -> None:
    """
    Background thread: poll FD count and snapshot until process exits.
    """
    while not stop_event.is_set():
        if not os.path.exists(f"/proc/{pid}"):
            break
        count = _count_fds(pid)
        if count >= 0:
            fd_samples.append({"time_sec": round(time.monotonic(), 3), "fd_count": count})
            last_fd_snapshot["entries"] = _read_fds(pid)
        time.sleep(FD_SAMPLE_INTERVAL_SEC)


def execute_code_safely(
    script_path: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    fd_limit: int = DEFAULT_FD_LIMIT,
    python_executable: Optional[str] = None,
) -> dict:
    """
    Execute a Python script safely with timeout and FD limits.
    Samples FD count during execution and captures final FD snapshot.

    Returns a structured execution report:
    - pid: process ID
    - duration_seconds: wall-clock time
    - termination_reason: "normal" | "timeout" | "error"
    - exit_code: process exit code (or None if killed)
    - stdout, stderr: captured output (always str)
    - fd_samples: list of {time_sec, fd_count}
    - fd_snapshot: list of {fd, target} at last sample
    """
    if timeout_sec <= 0:
        timeout_sec = DEFAULT_TIMEOUT_SEC
    if fd_limit <= 0:
        fd_limit = DEFAULT_FD_LIMIT

    python = python_executable or "python3"
    abs_script = os.path.abspath(script_path)
    cwd = os.path.dirname(abs_script) or "."

    def set_limits():
        resource.setrlimit(resource.RLIMIT_NOFILE, (fd_limit, fd_limit))

    fd_samples: list = []
    last_fd_snapshot: dict = {"entries": []}
    stop_event = threading.Event()

    start = time.monotonic()
    sampling_started_at = datetime.now(timezone.utc).isoformat()
    proc = subprocess.Popen(
        [python, abs_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=set_limits if os.name == "posix" else None,
        cwd=cwd,
        start_new_session=True,
    )
    pid = proc.pid
    logger.info(
        "Execution started pid=%s path=%s timeout=%s fd_limit=%s",
        pid, abs_script, timeout_sec, fd_limit,
    )

    sampler = threading.Thread(
        target=_fd_sampler,
        args=(pid, fd_samples, last_fd_snapshot, stop_event),
        daemon=True,
    )
    sampler.start()

    termination_reason: str
    exit_code: Optional[int]
    stdout_bytes: bytes
    stderr_bytes: bytes

    try:
        stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_sec)
        exit_code = proc.returncode
        termination_reason = "normal" if exit_code == 0 else "error"
    except subprocess.TimeoutExpired:
        logger.warning("Execution timeout pid=%s after %ss", pid, timeout_sec)
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            proc.kill()
        proc.wait()
        stdout_bytes = proc.stdout.read() if proc.stdout else b""
        stderr_bytes = proc.stderr.read() if proc.stderr else b""
        exit_code = None
        termination_reason = "timeout"

    stop_event.set()
    sampler.join(timeout=1.0)
    duration_seconds = round(time.monotonic() - start, 3)

    stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

    combined_err = (stdout_str + stderr_str).lower()
    if any(ind in combined_err for ind in FD_LIMIT_VIOLATION_INDICATORS):
        logger.warning("FD limit violation detected pid=%s fd_limit=%s", pid, fd_limit)

    logger.info(
        "Execution finished pid=%s duration=%.3fs reason=%s",
        pid, duration_seconds, termination_reason,
    )

    t0 = fd_samples[0]["time_sec"] if fd_samples else 0
    normalized_samples = [
        {"time_sec": round(s["time_sec"] - t0, 3), "fd_count": s["fd_count"]}
        for s in fd_samples
    ]
    snapshot_taken_at = datetime.now(timezone.utc).isoformat()

    return {
        "pid": pid,
        "duration_seconds": duration_seconds,
        "termination_reason": termination_reason,
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "fd_samples": normalized_samples,
        "fd_snapshot": last_fd_snapshot.get("entries", []),
        "timeout_sec": timeout_sec,
        "fd_limit": fd_limit,
        "sampling_started_at": sampling_started_at,
        "snapshot_taken_at": snapshot_taken_at,
    }


def compile_c(source_path: str, binary_name: str = "program") -> tuple[bool, str, str, Optional[str]]:
    """
    Compile a C source file using gcc.
    No shell. Direct invocation: gcc source.c -o program.

    Returns (success, stdout, stderr, binary_path).
    binary_path is set only when success is True.
    """
    abs_source = os.path.abspath(source_path)
    cwd = os.path.dirname(abs_source) or "."
    binary_path = os.path.join(cwd, binary_name)

    result = subprocess.run(
        ["gcc", abs_source, "-o", binary_path],
        capture_output=True,
        cwd=cwd,
        timeout=60,
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    success = result.returncode == 0
    return (success, stdout, stderr, binary_path if success else None)


def execute_binary_safely(
    binary_path: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    fd_limit: int = DEFAULT_FD_LIMIT,
) -> dict:
    """
    Execute a compiled binary safely with timeout and FD limits.
    Same sandbox as execute_code_safely: RLIMIT_NOFILE, FD sampling, killpg on timeout.

    Returns the same structure as execute_code_safely.
    """
    if timeout_sec <= 0:
        timeout_sec = DEFAULT_TIMEOUT_SEC
    if fd_limit <= 0:
        fd_limit = DEFAULT_FD_LIMIT

    abs_binary = os.path.abspath(binary_path)
    cwd = os.path.dirname(abs_binary) or "."

    def set_limits():
        resource.setrlimit(resource.RLIMIT_NOFILE, (fd_limit, fd_limit))

    fd_samples: list = []
    last_fd_snapshot: dict = {"entries": []}
    stop_event = threading.Event()

    start = time.monotonic()
    sampling_started_at = datetime.now(timezone.utc).isoformat()
    proc = subprocess.Popen(
        [abs_binary],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=set_limits if os.name == "posix" else None,
        cwd=cwd,
        start_new_session=True,
    )
    pid = proc.pid
    logger.info(
        "Execution started pid=%s path=%s timeout=%s fd_limit=%s",
        pid, abs_binary, timeout_sec, fd_limit,
    )

    sampler = threading.Thread(
        target=_fd_sampler,
        args=(pid, fd_samples, last_fd_snapshot, stop_event),
        daemon=True,
    )
    sampler.start()

    termination_reason: str
    exit_code: Optional[int]
    stdout_bytes: bytes
    stderr_bytes: bytes

    try:
        stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_sec)
        exit_code = proc.returncode
        termination_reason = "normal" if exit_code == 0 else "error"
    except subprocess.TimeoutExpired:
        logger.warning("Execution timeout pid=%s after %ss", pid, timeout_sec)
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            proc.kill()
        proc.wait()
        stdout_bytes = proc.stdout.read() if proc.stdout else b""
        stderr_bytes = proc.stderr.read() if proc.stderr else b""
        exit_code = None
        termination_reason = "timeout"

    stop_event.set()
    sampler.join(timeout=1.0)
    duration_seconds = round(time.monotonic() - start, 3)

    stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

    combined_err = (stdout_str + stderr_str).lower()
    if any(ind in combined_err for ind in FD_LIMIT_VIOLATION_INDICATORS):
        logger.warning("FD limit violation detected pid=%s fd_limit=%s", pid, fd_limit)

    logger.info(
        "Execution finished pid=%s duration=%.3fs reason=%s",
        pid, duration_seconds, termination_reason,
    )

    t0 = fd_samples[0]["time_sec"] if fd_samples else 0
    normalized_samples = [
        {"time_sec": round(s["time_sec"] - t0, 3), "fd_count": s["fd_count"]}
        for s in fd_samples
    ]
    snapshot_taken_at = datetime.now(timezone.utc).isoformat()

    return {
        "pid": pid,
        "duration_seconds": duration_seconds,
        "termination_reason": termination_reason,
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "fd_samples": normalized_samples,
        "fd_snapshot": last_fd_snapshot.get("entries", []),
        "timeout_sec": timeout_sec,
        "fd_limit": fd_limit,
        "sampling_started_at": sampling_started_at,
        "snapshot_taken_at": snapshot_taken_at,
    }
