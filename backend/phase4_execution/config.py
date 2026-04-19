"""Configuration for Phase 4 — Execution Agent.

Handles credentials for Gemini (Booking & Cancellation Agents) and Google Workspace MCP tools.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


# --- Gemini (Booking & Cancellation Agents) ---
GEMINI_ACTIONS_API_KEY: str = os.getenv("GEMINI_ACTIONS_API_KEY", "")
GEMINI_ACTIONS_MODEL_NAME: str = os.getenv("GEMINI_ACTIONS_MODEL_NAME", "gemini-2.5-flash")
GEMINI_ACTIONS_FALLBACK_API_KEY: str = os.getenv("GEMINI_ACTIONS_FALLBACK_API_KEY", "")
GEMINI_ACTIONS_FALLBACK_MODEL_NAME: str = os.getenv(
    "GEMINI_ACTIONS_FALLBACK_MODEL_NAME", "gemini-2.5-flash"
)


# --- Google OAuth & Calendar ---
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")


# --- Google Docs ---
GOOGLE_DOCS_FOLDER_ID: str = os.getenv("GOOGLE_DOCS_FOLDER_ID", "")


# --- Gmail ---
MF_DISTRIBUTOR_EMAIL: str = os.getenv("MF_DISTRIBUTOR_EMAIL", "")


# --- Google Sheets ---
GOOGLE_SPREADSHEET_ID: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")
GOOGLE_SHEET_NAME: str = os.getenv("GOOGLE_SHEET_NAME", "Meetings Log")


def get_gemini_actions_credentials(use_fallback: bool = False) -> dict:
    """Return the API key and model name for the Gemini Actions Agent.
    
    Used by both Booking Agent and Cancellation Agent.
    Falls back to the secondary credentials when use_fallback is True.
    """
    if use_fallback:
        return {
            "api_key": GEMINI_ACTIONS_FALLBACK_API_KEY,
            "model": GEMINI_ACTIONS_FALLBACK_MODEL_NAME,
        }
    return {
        "api_key": GEMINI_ACTIONS_API_KEY,
        "model": GEMINI_ACTIONS_MODEL_NAME,
    }


def get_google_credentials() -> dict:
    """Return Google OAuth credentials for MCP tools."""
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "calendar_id": GOOGLE_CALENDAR_ID,
    }


def get_google_docs_config() -> dict:
    """Return Google Docs configuration."""
    return {
        "folder_id": GOOGLE_DOCS_FOLDER_ID,
    }


def get_gmail_config() -> dict:
    """Return Gmail configuration."""
    return {
        "recipient_email": MF_DISTRIBUTOR_EMAIL,
    }


def get_google_sheets_config() -> dict:
    """Return Google Sheets configuration."""
    return {
        "spreadsheet_id": GOOGLE_SPREADSHEET_ID,
        "sheet_name": GOOGLE_SHEET_NAME,
    }
