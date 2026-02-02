"""
Gemini API client for FD execution report summarization.
Produces deterministic, technical summaries for systems/security engineers.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _build_prompt(report: dict) -> str:
    """Build a systems-engineer style prompt for FD analysis summarization."""
    language = report.get("execution", {}).get("language", "python")
    return f"""You are a senior systems/security engineer analyzing a file descriptor forensics report from a Linux code execution sandbox.

Language: {language}

Analyze the following structured report and produce a concise technical summary. Be deterministic and factual. No fluff.

REPORT (JSON):
{json.dumps(report, indent=2)}

Provide your analysis in the following structure (use these exact section headers):

## FD Leaks Detected
List any indications of FD leaks (monotonically growing fd_count, high final count relative to expected, leaks at exit). If none, state "No clear leak indicators."

## Root Cause
Identify the likely cause from the FD types (Standard, File, Pipe, Socket, Other), execution behavior, termination reason, and language. For compile_error, focus on the compilation failures.

## Severity
State the severity (LOW/MEDIUM/HIGH/CRITICAL) and one-sentence justification.

## Fix Recommendations
Specific, actionable recommendations. If no issues, state "No changes required."
"""


def summarize_fd_report(report: dict) -> Optional[str]:
    """
    Send the FD execution report to Gemini and return a human-readable summary.
    Returns None if API key is missing, invalid, or the request fails.
    Output is always a string when successful; None indicates fallback is needed.
    """
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.debug("GEMINI_API_KEY not set, skipping AI summarization")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = _build_prompt(report)
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        return str(text) if text is not None else None
    except Exception as e:
        logger.warning("Gemini API request failed: %s", e)
        return None
