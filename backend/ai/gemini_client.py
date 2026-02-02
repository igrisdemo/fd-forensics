"""
Gemini API client for FD execution report summarization.
Produces deterministic, technical summaries for systems/security engineers.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project root (backend/ai -> backend -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _ensure_env_loaded() -> None:
    """Load .env from project root so GEMINI_API_KEY is available regardless of cwd."""
    try:
        from dotenv import load_dotenv
        env_path = _PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _build_prompt(report: dict) -> str:
    """Build a strict forensic prompt; response must use exact section headers, max 250 words."""
    language = report.get("execution", {}).get("language", "python")
    return f"""You are a senior systems/security engineer performing file descriptor forensics. Respond using EXACTLY the four section headers below. No filler, no generic advice, no repetition. Maximum 250 words.

REPORT (JSON):
{json.dumps(report, indent=2)}

Use exactly these headers and requirements:

### FD Forensic Summary
- Language: Python or C (from report)
- Termination: normal | timeout | compile_error
- Max FD count observed (from fd_growth or fd_snapshot)
- FD growth pattern: linear | burst | plateau | leak-like (from fd_growth time-series)

### Risk Assessment
- Is this behavior expected for this code? Yes/No and why
- Leak likelihood: Low | Medium | High
- Dominant FD type and why it matters

### Evidence
- Specific FD numbers or types involved (from report)
- Growth timeline references (time_sec, fd_count from fd_growth)

### Actionable Recommendations
- Concrete fixes: close(), context managers, socket handling, etc.
- If no leak: state explicitly why
"""


def summarize_fd_report(report: dict) -> Optional[str]:
    """
    Send the FD execution report to Gemini and return a human-readable summary.
    Returns None if API key is missing, invalid, or the request fails.
    Output is always a string when successful; None indicates fallback is needed.
    """
    _ensure_env_loaded()
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.debug("GEMINI_API_KEY NOT SET")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = _build_prompt(report)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 512,
                "top_p": 0.95,
            },
        )
        text = getattr(response, "text", None)
        if text is not None:
            return str(text).strip()
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            text = getattr(part, "text", None)
            return str(text).strip() if text else None
        logger.warning("Gemini returned no text")
        return None
    except Exception as e:
        logger.warning("Gemini API request failed: %s", e)
        return None
