"""
PDF report generation for File Descriptor Forensics and Code Sandbox.
Produces readable text/tables, no charts.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors


def _to_str(x: Any) -> str:
    if x is None:
        return "—"
    return str(x)


def _build_process_report(
    buffer: BytesIO,
    pid: int,
    data: dict,
) -> None:
    """Build PDF for live process analysis."""
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("File Descriptor Forensics and Code Sandbox", styles["Title"]))
    story.append(Paragraph(f"Live Process Analysis — PID {pid}", styles["Heading2"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    if data.get("snapshot_taken_at"):
        story.append(Paragraph(f"Snapshot taken (UTC): {data['snapshot_taken_at']}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Metrics
    story.append(Paragraph("Metrics", styles["Heading3"]))
    total = len(data.get("table", []) or [])
    metrics_data = [
        ["Total FDs", _to_str(total)],
        ["Non-Standard", _to_str(data.get("non_standard"))],
        ["FD Density", _to_str(f"{data.get('fd_density', 0):.2f}" if isinstance(data.get("fd_density"), (int, float)) else data.get("fd_density"))],
        ["Severity", _to_str(data.get("severity"))],
    ]
    if data.get("usage_pct") is not None:
        metrics_data.append(["Usage vs Limit", f"{data['usage_pct']:.1f}%"])
    t = Table(metrics_data, colWidths=[2 * inch, 2 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Severity rationale: {data.get('severity_reason', '')}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # Interpretation
    if data.get("analysis"):
        story.append(Paragraph("Forensic Interpretation", styles["Heading3"]))
        for line in data["analysis"]:
            story.append(Paragraph(f"• {line}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

    # Type breakdown
    type_counts = data.get("type_counts") or {}
    fd_danger_reason = data.get("fd_danger_reason") or {}
    if type_counts:
        story.append(Paragraph("FD Type Breakdown", styles["Heading3"]))
        for t, count in type_counts.items():
            reason = fd_danger_reason.get(t, "")
            story.append(Paragraph(f"{t}: {count} — {reason}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

    # FD table (paginated)
    table_data = data.get("table") or []
    if table_data:
        story.append(Paragraph("File Descriptor Table", styles["Heading3"]))
        rows_per_page = 25
        for i in range(0, len(table_data), rows_per_page):
            chunk = table_data[i : i + rows_per_page]
            tbl_rows = [["FD", "Target", "Type"]]
            for row in chunk:
                fd = row.get("FD", row.get("fd", ""))
                target = row.get("Target", row.get("target", "")) or "—"
                typ = row.get("Type", row.get("type", "")) or "—"
                tbl_rows.append([_to_str(fd), str(target)[:80], _to_str(typ)])
            t = Table(tbl_rows, colWidths=[0.6 * inch, 4 * inch, 1 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t)
            if i + rows_per_page < len(table_data):
                story.append(PageBreak())

    doc.build(story)


def _build_code_report(
    buffer: BytesIO,
    raw_analysis: dict,
    ai_summary: str,
) -> None:
    """Build PDF for code analysis run."""
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("File Descriptor Forensics and Code Sandbox", styles["Title"]))
    story.append(Paragraph("Code Analysis", styles["Heading2"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    exec_meta = raw_analysis.get("execution") or {}
    if exec_meta.get("sampling_started_at"):
        story.append(Paragraph(f"Execution snapshot at: {exec_meta['sampling_started_at']}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Execution metadata
    story.append(Paragraph("Execution Metadata", styles["Heading3"]))
    exec_rows = [
        ["Language", _to_str(exec_meta.get("language"))],
        ["PID", _to_str(exec_meta.get("pid"))],
        ["Duration", f"{exec_meta.get('duration_seconds', 0)}s" if exec_meta.get("duration_seconds") is not None else "—"],
        ["Termination", _to_str(exec_meta.get("termination_reason"))],
        ["Exit Code", _to_str(exec_meta.get("exit_code"))],
        ["FD Limit", _to_str(exec_meta.get("fd_limit"))],
    ]
    if exec_meta.get("snapshot_taken_at"):
        exec_rows.append(["Snapshot taken (UTC)", exec_meta["snapshot_taken_at"]])
    t = Table(exec_rows, colWidths=[1.5 * inch, 2 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    story.append(t)

    if exec_meta.get("stdout"):
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("stdout:", styles["Normal"]))
        story.append(Paragraph(exec_meta["stdout"][:2000].replace("\n", "<br/>"), ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8)))
    if exec_meta.get("stderr"):
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("stderr:", styles["Normal"]))
        story.append(Paragraph(exec_meta["stderr"][:2000].replace("\n", "<br/>"), ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8)))

    story.append(Spacer(1, 0.3 * inch))

    # FD growth summary (text)
    fd_growth = raw_analysis.get("fd_growth") or []
    if fd_growth:
        story.append(Paragraph("FD Growth", styles["Heading3"]))
        n = len(fd_growth)
        t0 = fd_growth[0].get("time_sec", 0) if fd_growth else 0
        t1 = fd_growth[-1].get("time_sec", 0) if fd_growth else 0
        max_count = max((p.get("fd_count", 0) for p in fd_growth), default=0)
        story.append(Paragraph(
            f"Sample count: {n}; time range: {t0}–{t1} s; max FD count: {max_count}",
            styles["Normal"],
        ))
        story.append(Spacer(1, 0.2 * inch))

    # FD analysis (if present)
    fd_analysis = raw_analysis.get("fd_analysis")
    if fd_analysis:
        story.append(Paragraph("FD Analysis", styles["Heading3"]))
        metrics_rows = [
            ["Total FDs", _to_str(len(fd_analysis.get("table") or []))],
            ["Non-Standard", _to_str(fd_analysis.get("non_standard"))],
            ["Severity", _to_str(fd_analysis.get("severity"))],
            ["FD Density", _to_str(f"{fd_analysis.get('fd_density', 0):.2f}" if isinstance(fd_analysis.get("fd_density"), (int, float)) else fd_analysis.get("fd_density"))],
        ]
        t = Table(metrics_rows, colWidths=[1.5 * inch, 2 * inch])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

        table_data = fd_analysis.get("table") or []
        if table_data:
            story.append(Paragraph("File Descriptor Table", styles["Heading3"]))
            rows_per_page = 25
            for i in range(0, len(table_data), rows_per_page):
                chunk = table_data[i : i + rows_per_page]
                tbl_rows = [["FD", "Target", "Type"]]
                for row in chunk:
                    fd = row.get("FD", row.get("fd", ""))
                    target = row.get("Target", row.get("target", "")) or "—"
                    typ = row.get("Type", row.get("type", "")) or "—"
                    tbl_rows.append([_to_str(fd), str(target)[:80], _to_str(typ)])
                t = Table(tbl_rows, colWidths=[0.6 * inch, 4 * inch, 1 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(t)
                if i + rows_per_page < len(table_data):
                    story.append(PageBreak())
        story.append(Spacer(1, 0.3 * inch))

    # AI forensic summary
    if ai_summary:
        story.append(Paragraph("AI Forensic Summary", styles["Heading3"]))
        for line in ai_summary.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("###"):
                story.append(Paragraph(line[3:].strip(), styles["Heading4"]))
            elif line.startswith("##"):
                story.append(Paragraph(line[2:].strip(), styles["Heading4"]))
            else:
                story.append(Paragraph(line.replace("<", "&lt;").replace(">", "&gt;"), styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)


def generate_process_pdf(pid: int, data: dict) -> bytes:
    """Generate PDF bytes for live process analysis."""
    buffer = BytesIO()
    _build_process_report(buffer, pid, data)
    return buffer.getvalue()


def generate_code_pdf(raw_analysis: dict, ai_summary: str) -> bytes:
    """Generate PDF bytes for code analysis run."""
    buffer = BytesIO()
    _build_code_report(buffer, raw_analysis, ai_summary)
    return buffer.getvalue()
