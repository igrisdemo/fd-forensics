from collections import Counter
from analysis.fd_classifier import classify_fd

FD_DANGER_RANK = {
    "Standard": 1,
    "File": 2,
    "Pipe": 3,
    "Other": 4,
    "Socket": 5
}

FD_DANGER_REASON = {
    "Standard": "Standard file descriptors (stdin, stdout, stderr) are always present and are automatically managed by the OS.",
    "File": "Regular file descriptors may hold inode references and file locks, which can delay resource release if leaked.",
    "Pipe": "Pipes involve kernel buffers and IPC synchronization, making leaks more impactful under load.",
    "Other": "Other descriptors often map to device files or anonymous kernel objects with less predictable lifetimes.",
    "Socket": "Sockets maintain kernel networking state, buffers, and remote connections, making leaks highly dangerous."
}

def analyze_fds(fd_entries, soft_limit):
    report = []
    types = []
    non_standard = 0

    for entry in fd_entries:
        fd_type = classify_fd(entry["target"], entry["fd"])
        types.append(fd_type)

        if fd_type != "Standard":
            non_standard += 1

        report.append({
            "FD": entry["fd"],
            "Target": entry["target"],
            "Type": fd_type
        })

    type_counts = Counter(types)
    total = len(fd_entries)

    # -----------------------------
    # FD Density (Kernel Intensity)
    # -----------------------------
    fd_density = non_standard / total if total > 0 else 0.0

    # -----------------------------
    # FD Usage vs Soft Limit
    # -----------------------------
    usage_pct = None
    if isinstance(soft_limit, int) and soft_limit > 0:
        usage_pct = (total / soft_limit) * 100

    # -----------------------------
    # Severity Classification
    # -----------------------------
    if usage_pct is not None and usage_pct >= 90:
        severity = "CRITICAL"
        severity_reason = "FD usage is extremely high and approaches the configured per-process limit."
        severity_condition = "FD usage percentage ≥ 90% of the soft limit."

    elif usage_pct is not None and usage_pct >= 70:
        severity = "HIGH"
        severity_reason = "FD usage is significantly elevated relative to the allowed limit."
        severity_condition = "FD usage percentage between 70% and 90% of the soft limit."

    elif total >= 200:
        severity = "MEDIUM"
        severity_reason = "The absolute number of open file descriptors is high compared to typical processes."
        severity_condition = "Total open file descriptors ≥ 200, regardless of percentage."

    else:
        severity = "LOW"
        severity_reason = "The process maintains a controlled number of file descriptors."
        severity_condition = "Total open file descriptors < 200 and usage well within limits."

    # -----------------------------
    # Range-Based Interpretation
    # -----------------------------
    analysis = []

    if total < 50:
        analysis.append(
            "The process has a very small file descriptor footprint, typical of short-lived or idle programs."
        )
    elif total < 100:
        analysis.append(
            "The process shows low file descriptor usage, common for lightweight background services."
        )
    elif total < 150:
        analysis.append(
            "The file descriptor usage is moderate and consistent with normal file and IPC activity."
        )
    elif total < 200:
        analysis.append(
            "The process maintains a moderately high number of file descriptors, indicating sustained kernel interaction."
        )
    else:
        analysis.append(
            "The process exhibits very high file descriptor usage, typical of browsers, IDEs, or core services."
        )

    analysis.append(
        f"{non_standard} out of {total} descriptors are non-standard and correspond to kernel-managed resources."
    )

    analysis.append(
        "High file descriptor usage does not necessarily indicate a resource leak, but it increases the potential impact if descriptors are not properly released."
    )

    analysis.append(
        "Processes dominated by sockets and pipes pose a higher forensic risk than those dominated by regular files, due to greater retained kernel state."
    )

    return {
        "table": report,
        "type_counts": type_counts,
        "non_standard": non_standard,
        "severity": severity,
        "severity_reason": severity_reason,
        "severity_condition": severity_condition,
        "analysis": analysis,
        "usage_pct": usage_pct,
        "fd_density": fd_density,
        "fd_danger_rank": FD_DANGER_RANK,
        "fd_danger_reason": FD_DANGER_REASON
    }
