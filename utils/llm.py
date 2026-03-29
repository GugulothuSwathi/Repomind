# utils/llm.py
# ============================================
# RepoMind - Gemini AI Helper
#
# This file is a simple wrapper around the
# Google Gemini API. Every agent uses this
# to talk to the AI — so we keep it in one place.
# ============================================

import os
from typing import Any

from utils.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_CA_BUNDLE


def _get_modern_genai() -> tuple[Any | None, Any | None]:
    """Load the modern google.genai client lazily.

    Keeping this import lazy avoids import-time failures if the package
    is not available yet and lets us fall back gracefully.
    """
    try:
        from google import genai as modern_genai
        from google.genai import types as modern_types
        return modern_genai, modern_types
    except Exception:
        return None, None


def _get_legacy_genai() -> Any | None:
    """Load the deprecated google.generativeai package only if needed."""
    try:
        import google.generativeai as legacy_genai
        return legacy_genai
    except Exception:
        return None


def get_gemini_response(prompt: str, temperature: float = 0.35, max_retries: int = 4) -> str:
    """
    Send a prompt to Gemini and return the text response.

    Args:
        prompt      : The full text prompt to send to the AI
        temperature : 0.0 = very focused/deterministic
                      1.0 = more creative/random
                      0.35 balances focus with flexibility for better answers
        max_retries : Max number of retries before failing on quota errors

    Returns:
        The AI's response as a plain string.
        If something goes wrong, returns an error message.
    """
    import time

    # Optional corporate/proxy root CA bundle for SSL interception environments.
    if GEMINI_CA_BUNDLE:
        os.environ["SSL_CERT_FILE"] = GEMINI_CA_BUNDLE
        os.environ["REQUESTS_CA_BUNDLE"] = GEMINI_CA_BUNDLE
        os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = GEMINI_CA_BUNDLE
    for attempt in range(max_retries):
        try:
            if not GEMINI_API_KEY:
                return "⚠️ Gemini API Error: GEMINI_API_KEY is not set in your environment. Please add it to your .env file or Streamlit secrets."

            # Prefer modern SDK: google.genai
            modern_genai, modern_types = _get_modern_genai()
            if modern_genai is not None:
                client = modern_genai.Client(api_key=GEMINI_API_KEY)

                config_obj: Any = None
                if modern_types is not None:
                    cfg_cls = getattr(modern_types, "GenerateContentConfig", None)
                    if cfg_cls is not None:
                        config_obj = cfg_cls(temperature=temperature)

                req: dict[str, Any] = {
                    "model": GEMINI_MODEL,
                    "contents": prompt,
                }
                if config_obj is not None:
                    req["config"] = config_obj

                response = client.models.generate_content(**req)
                return getattr(response, "text", str(response))

            # Fallback for older environments: google.generativeai
            legacy_genai = _get_legacy_genai()
            if legacy_genai is None:
                return "⚠️ Gemini API Error: No supported Gemini SDK found. Install google-genai."

            configure_fn = getattr(legacy_genai, "configure", None)
            if callable(configure_fn):
                configure_fn(api_key=GEMINI_API_KEY)

            generation_config: Any = {"temperature": temperature}
            types_ns = getattr(legacy_genai, "types", None)
            generation_cfg_cls = getattr(types_ns, "GenerationConfig", None) if types_ns else None
            if generation_cfg_cls:
                generation_config = generation_cfg_cls(temperature=temperature)

            model_cls = getattr(legacy_genai, "GenerativeModel", None)
            if model_cls is None:
                return "⚠️ Gemini API Error: Unsupported google-generativeai package version."

            try:
                model = model_cls(model_name=GEMINI_MODEL, generation_config=generation_config)
            except TypeError:
                model = model_cls(GEMINI_MODEL)

            try:
                response = model.generate_content(prompt, generation_config=generation_config)
            except TypeError:
                response = model.generate_content(prompt)

            return getattr(response, "text", str(response))

        except Exception as e:
            # If anything goes wrong, return a readable error with more details
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                return f"⚠️ Gemini API Quota Exceeded: {str(e)}\n\nPlease try again in a few moments."
            elif "api" in error_msg or "key" in error_msg:
                return f"⚠️ Gemini API Error: Authentication failed. Check your GEMINI_API_KEY in .env or Streamlit secrets.\n\nDetails: {str(e)}"
            elif "timeout" in error_msg or "connection" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return f"⚠️ Connection Error: {str(e)}\n\nCheck your internet connection and try again."
            elif (
                "certificate_verify_failed" in error_msg
                or "self-signed certificate" in error_msg
                or "ssl" in error_msg and "certificate" in error_msg
            ):
                return (
                    "⚠️ Gemini SSL Certificate Error: Python could not verify the HTTPS certificate chain.\n\n"
                    "This is usually caused by a corporate proxy / antivirus TLS inspection with a self-signed root CA.\n\n"
                    "Try one of these fixes:\n"
                    "1) Install/update root certificates on your machine\n"
                    "2) Set REQUESTS_CA_BUNDLE or SSL_CERT_FILE to your org/root CA PEM path\n"
                    "3) Ask your network admin to allow direct TLS trust for Gemini endpoints\n\n"
                    f"Details: {str(e)}"
                )
            else:
                return f"⚠️ Gemini API Error: {str(e)}\n\nMake sure your GEMINI_API_KEY is set correctly in .env"


def get_gemini_response_json(prompt: str) -> str:
    """
    Like get_gemini_response but asks Gemini to return JSON.
    Useful when agents need structured data.
    """
    json_prompt = prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
    return get_gemini_response(json_prompt, temperature=0.1)