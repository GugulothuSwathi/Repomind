# utils/llm.py
# ============================================
# RepoMind - Gemini AI Helper
#
# This file is a simple wrapper around the
# Google Gemini API. Every agent uses this
# to talk to the AI — so we keep it in one place.
# ============================================

from typing import Any

from utils.config import GEMINI_API_KEY, GEMINI_MODEL


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


def get_gemini_response(prompt: str, temperature: float = 0.3) -> str:
    """
    Send a prompt to Gemini and return the text response.

    Args:
        prompt      : The full text prompt to send to the AI
        temperature : 0.0 = very focused/deterministic
                      1.0 = more creative/random
                      0.3 is a good balance for code analysis

    Returns:
        The AI's response as a plain string.
        If something goes wrong, returns an error message.
    """
    try:
        if not GEMINI_API_KEY:
            return "⚠️ Gemini API Error: GEMINI_API_KEY is not set in your environment."

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
        # If anything goes wrong, return a readable error
        return f"⚠️ Gemini API Error: {str(e)}\n\nMake sure your GEMINI_API_KEY is set correctly in .env"


def get_gemini_response_json(prompt: str) -> str:
    """
    Like get_gemini_response but asks Gemini to return JSON.
    Useful when agents need structured data.
    """
    json_prompt = prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
    return get_gemini_response(json_prompt, temperature=0.1)