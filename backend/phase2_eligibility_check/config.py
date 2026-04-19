import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


# --- Gemini (Eligibility Agent) ---
GEMINI_ELIGIBILITY_API_KEY: str = os.getenv("GEMINI_ELIGIBILITY_API_KEY", "")
GEMINI_ELIGIBILITY_MODEL_NAME: str = os.getenv(
    "GEMINI_ELIGIBILITY_MODEL_NAME", "gemini-2.5-flash"
)
GEMINI_ELIGIBILITY_FALLBACK_API_KEY: str = os.getenv(
    "GEMINI_ELIGIBILITY_FALLBACK_API_KEY", ""
)
GEMINI_ELIGIBILITY_FALLBACK_MODEL_NAME: str = os.getenv(
    "GEMINI_ELIGIBILITY_FALLBACK_MODEL_NAME", "gemini-2.5-flash"
)


# --- Google OAuth & Calendar ---
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")


# --- Knowledge Base ---
KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge_base")


def get_gemini_eligibility_credentials(use_fallback: bool = False) -> dict:
    """Return the API key and model name for the Gemini Eligibility Agent.
    Falls back to the secondary credentials when use_fallback is True."""
    if use_fallback:
        return {
            "api_key": GEMINI_ELIGIBILITY_FALLBACK_API_KEY,
            "model": GEMINI_ELIGIBILITY_FALLBACK_MODEL_NAME,
        }
    return {
        "api_key": GEMINI_ELIGIBILITY_API_KEY,
        "model": GEMINI_ELIGIBILITY_MODEL_NAME,
    }


def get_google_credentials() -> dict:
    """Return Google OAuth credentials for MCP tools."""
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "calendar_id": GOOGLE_CALENDAR_ID,
    }
