import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


# --- Groq (Orchestrator Agent) ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

GROQ_FALLBACK_API_KEY: str = os.getenv("GROQ_FALLBACK_API_KEY", "")
GROQ_FALLBACK_MODEL_NAME: str = os.getenv(
    "GROQ_FALLBACK_MODEL_NAME", "llama-3.3-70b-versatile"
)


def get_groq_credentials(use_fallback: bool = False) -> dict:
    """Return the API key and model name for the Groq LLM.
    Falls back to the secondary credentials when use_fallback is True."""
    if use_fallback:
        return {
            "api_key": GROQ_FALLBACK_API_KEY,
            "model": GROQ_FALLBACK_MODEL_NAME,
        }
    return {
        "api_key": GROQ_API_KEY,
        "model": GROQ_MODEL_NAME,
    }
