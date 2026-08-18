"""
LLM Client Helper — Centralized Robust Gemini Wrapper with Model Fallbacks
==========================================================================
Handles API key resolution, model initialization, and automatic model fallbacks
if a specific model is deprecated or unavailable.
"""

import os
import sys
from pathlib import Path
from google import genai
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

AGENTS_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=AGENTS_DIR / '.env')

PREFERRED_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]


def get_gemini_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("[ERROR] GEMINI_API_KEY is not set in ai_agents/.env")
        sys.exit(1)
    return genai.Client(api_key=key)


def generate_text_with_retry(client: genai.Client, prompt: str, models: list[str] = None) -> str:
    """
    Generate content with Gemini, automatically falling back across candidate models
    if a 404 or model-not-found error is returned.
    """
    model_list = models or PREFERRED_MODELS
    last_error = None

    for model_name in model_list:
        try:
            resp = client.models.generate_content(model=model_name, contents=prompt)
            return resp.text.strip()
        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()
            if "not_found" in err_str or "no longer available" in err_str or "404" in err_str or "invalid" in err_str:
                continue
            # If it's a rate limit or other error, raise or try next
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
