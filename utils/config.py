# utils/config.py
# ============================================
# RepoMind - Central Configuration
# This file loads your API keys and settings.
# ============================================

import os
from dotenv import load_dotenv

# Load .env file automatically when this module is imported
load_dotenv()


def _get_secret(name: str, default: str = "") -> str:
    """Read secrets from env first, then Streamlit Cloud secrets."""
    value = os.getenv(name, "")
    if value:
        return value

    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except Exception:
        return default

# ---- API Keys ----
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY", "")
GITHUB_TOKEN   = _get_secret("GITHUB_TOKEN", "")

# ---- Model Settings ----
# gemini-1.5-flash is FREE and very fast — perfect for hackathon
GEMINI_MODEL = "gemini-2.0-flash"

# ---- Risk Score Weights ----
# These weights decide how the overall risk score is calculated.
# You can tweak these values to change priority.
RISK_WEIGHTS = {
    "security_issues": 0.40,   # 40% weight — most critical
    "complexity":      0.30,   # 30% weight — code maintainability
    "lint_errors":     0.20,   # 20% weight — code style
    "dependency_risk": 0.10,   # 10% weight — outdated packages
}

# ---- App Info ----
APP_NAME    = "RepoMind"
APP_VERSION = "1.0.0"
APP_TAGLINE = "AI-Powered Repository Intelligence"