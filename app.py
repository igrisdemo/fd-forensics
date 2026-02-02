import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from proc.process_list import list_processes
from proc.process_info import get_fd_limits
from proc.fd_reader import read_fds
from analysis.report_builder import analyze_fds

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="FD Forensics – Linux OS",
    layout="wide"
)

# -----------------------------
# CENTERED MAIN HEADING
# -----------------------------
st.markdown(
    "<h1 style='text-align: center;'>File Descriptor Forensics Tool (Linux)</h1>",
    unsafe_allow_html=True
)

# Snapshot timestamp
st.caption(f"Snapshot captured at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# -----------------------------
# LOAD PROCESS SNAPSHOT
# -----------------------------
@st.cache_data(show_spinner=False)
def get_process_snapshot():
    return pd.DataFrame(list_processes())

proc_df = get_process_snapshot()

# -----------------------------
# SYSTEM OVERVIEW
# -----------------------------
st.markdown("## FD Usage Snapshot (System Overview)")

top5 = proc_df.sort_values("fd_count", ascending=False).head(5)[["pid", "name", "fd_count"]]
bottom5 = proc_df.sort_values("fd_count", ascending=True).head(5)[["pid", "name", "fd_count"]]

c1, c2 = st.columns(2)
with c1:
    st.markdown("### Top 5 FD-Heavy Processes")
    st.dataframe(top5, use_container_width=True)

with c2:
    st.markdown("### Bottom 5 FD-Light Processes")
    st.dataframe(bottom5, use_container_width=True)

# -----------------------------
# PROCESS SELECTION
# -----------------------------
if "selected_pid" not in st.session_state:
    st.session_state.selected_pid = int(proc_df.iloc[0]["pid"])

pid_list = proc_df["pid"].tolist()
name_map = dict(zip(proc_df["pid"], proc_df["name"]))

selected_pid = st.selectbox(
    "Select Process for Forensic Analysis",
    pid_list,
    index=pid_list.index(st.session_state.selected_pid),
    format_func=lambda p: f"{p} — {name_map[p]}"
)

st.session_state.selected_pid = selected_pid

# -----------------------------
# FD ANALYSIS
# -----------------------------
fds = read_fds(selected_pid)
soft, hard = get_fd_limits(selected_pid)
soft_limit = int(soft) if soft.isdigit() else None

result = analyze_fds(fds, soft_limit)

# -----------------------------
# PROCESS SUMMARY
# -----------------------------
st.markdown("## Process Summary")

st.metric("Total Open FDs", len(fds))
st.metric("Non-Standard FDs", result["non_standard"])
st.metric("FD Density (Kernel Usage)", f"{result['fd_density']:.2f}")

if result["usage_pct"] is not None:
    st.metric("FD Usage vs Soft Limit", f"{result['usage_pct']:.1f}%")

st.metric("Severity Level", result["severity"])
st.caption(f"Severity rationale: {result['severity_reason']}")
st.caption(f"Severity condition used: {result['severity_condition']}")

st.caption(
    "Note: A high number of open file descriptors does not by itself indicate a leak, "
    "but it increases the potential impact if descriptors are not properly released."
)

# -----------------------------
# DONUT CHART
# -----------------------------
st.markdown("## File Descriptor Risk Composition")

type_counts = result["type_counts"]
labels = list(type_counts.keys())
sizes = list(type_counts.values())

color_map = {
    "Standard": "#f5f5f5",
    "File": "#ffcc99",
    "Pipe": "#ff9966",
    "Other": "#ff704d",
    "Socket": "#cc0000"
}

colors = [color_map.get(l, "#cccccc") for l in labels]

left, center, right = st.columns([1, 2, 1])
with center:
    fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=120)
    ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        startangle=90,
        labeldistance=1.05,
        wedgeprops=dict(width=0.35, edgecolor="white")
    )
    ax.set_aspect("equal")
    ax.set_title("FD Type Distribution by Leak Risk", fontsize=10)
    st.pyplot(fig)

# -----------------------------
# FORENSIC INTERPRETATION
# -----------------------------
st.markdown("## Forensic Interpretation")
for line in result["analysis"]:
    st.write(f"- {line}")

# -----------------------------
# FD TYPE RISK EXPLANATION
# -----------------------------
st.markdown("### Interpretation of FD Risk Levels")

for fd_type in labels:
    count = type_counts[fd_type]
    reason = result["fd_danger_reason"][fd_type]
    st.write(f"- **{fd_type} ({count})**: {reason}")

st.markdown(
    "The severity classification reflects both the quantity of file descriptors and "
    "the dominance of higher-risk types such as sockets and pipes, which retain more kernel state."
)

# -----------------------------
# FD TABLE
# -----------------------------
st.markdown("## File Descriptor Table")
st.dataframe(pd.DataFrame(result["table"]), use_container_width=True)
