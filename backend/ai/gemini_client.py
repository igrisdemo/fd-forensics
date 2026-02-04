"""
Gemini API client for FD execution report summarization.
Produces deterministic, technical summaries for systems/security engineers.
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Optional, Tuple

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


def _sanitize_error_message(msg: str) -> str:
    """Remove any substring that could be an API key; never expose keys."""
    if not msg:
        return ""
    # Replace long alphanumeric/underscore strings (likely keys) with [REDACTED]
    out = re.sub(r"[A-Za-z0-9_-]{20,}", "[REDACTED]", msg)
    return out.strip()[:200]


def _classify_error(exc: Exception) -> Tuple[str, str]:
    """Return (error_code, sanitized_detail). Never include key in detail."""
    msg = (str(exc) or "").lower()
    detail = _sanitize_error_message(str(exc) or "")
    if "not valid" in msg or ("invalid" in msg and "key" in msg) or "api key" in msg:
        return ("invalid_key", detail or "API key rejected by Google.")
    if "400" in msg or "bad request" in msg:
        return ("invalid_key", detail or "Bad request (often invalid API key).")
    if "403" in msg or "permission" in msg or "forbidden" in msg:
        return ("invalid_key", detail or "Permission denied.")
    if "429" in msg or "quota" in msg or "rate limit" in msg or "resource exhausted" in msg:
        return ("quota", detail or "Rate limit exceeded.")
    if "blocked" in msg or "safety" in msg or "harm" in msg:
        return ("blocked", detail or "Response blocked.")
    if "network" in msg or "connection" in msg or "timeout" in msg or "timed out" in msg:
        return ("network", detail or "Network or timeout error.")
    if "404" in msg or "not found" in msg and ("model" in msg or "generateContent" in msg):
<<<<<<< HEAD
        return ("invalid_key", detail or "Model not found for this API. Try again; the app will use a supported model.")
=======
        return ("model_error", detail or "Model not found. Please check API availability.")
>>>>>>> 5daa7d3 (Gemini fix)
    return ("unknown", detail)


def summarize_fd_report(report: dict, api_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Send the FD execution report to Gemini.
    Returns (summary, error_code, detail). On success: (text, None, None).
    On failure: (None, error_code, sanitized_detail).
    """
    if not api_key:
        _ensure_env_loaded()
        api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.debug("GEMINI_API_KEY NOT SET")
        return (None, None, None)

    # Model names that support generateContent (try in order if one 404s)
<<<<<<< HEAD
    model_names = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
=======
    # Model names to try in order. prefer flash for speed/cost, then pro.
    # Model names to try in order. prefer flash-lite for quota, then flash.
    model_names = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-exp-1206",
    ]
>>>>>>> 5daa7d3 (Gemini fix)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        prompt = _build_prompt(report)
        config = {"temperature": 0.2, "max_output_tokens": 512, "top_p": 0.95}
        last_error: Optional[Exception] = None

        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=config)
                text = getattr(response, "text", None)
                if text is not None:
                    return (str(text).strip(), None, None)
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]
                    text = getattr(part, "text", None)
                    if text:
                        return (str(text).strip(), None, None)
                if response.candidates and response.candidates[0].finish_reason:
                    reason = str(response.candidates[0].finish_reason or "").lower()
                    if "safety" in reason or "block" in reason or "recitation" in reason:
                        return (None, "blocked", "Response was blocked by the model.")
                logger.warning("Gemini returned no text")
                return (None, "unknown", "Model returned no text.")
            except Exception as e:
                last_error = e
                err_msg = (str(e) or "").lower()
                if "404" in err_msg or "not found" in err_msg:
                    logger.debug("Model %s not available, trying next: %s", model_name, e)
                    continue
<<<<<<< HEAD
=======
                if "429" in err_msg or "quota" in err_msg or "resource exhausted" in err_msg:
                    logger.debug("Model %s quota exceeded, trying next: %s", model_name, e)
                    continue
>>>>>>> 5daa7d3 (Gemini fix)
                raise

        if last_error is not None:
            raise last_error
        return (None, "unknown", "Model returned no text.")
    except Exception as e:
        logger.warning("Gemini API request failed: %s", e)
        code, detail = _classify_error(e)
        return (None, code, detail)
