"""Configuration for Phase 3 — User Approval.

Environment variables and settings for the approval management system.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


# --- Approval Settings ---
# Time in minutes before an approval request expires
APPROVAL_EXPIRY_MINUTES: int = int(os.getenv("APPROVAL_EXPIRY_MINUTES", "10"))

# Maximum number of pending approvals to track per session
MAX_PENDING_APPROVALS_PER_SESSION: int = int(
    os.getenv("MAX_PENDING_APPROVALS_PER_SESSION", "5")
)

# Cleanup interval in minutes (how often to clean expired approvals)
APPROVAL_CLEANUP_INTERVAL_MINUTES: int = int(
    os.getenv("APPROVAL_CLEANUP_INTERVAL_MINUTES", "5")
)


def get_approval_settings() -> dict:
    """Return approval configuration settings."""
    return {
        "expiry_minutes": APPROVAL_EXPIRY_MINUTES,
        "max_pending_per_session": MAX_PENDING_APPROVALS_PER_SESSION,
        "cleanup_interval_minutes": APPROVAL_CLEANUP_INTERVAL_MINUTES,
    }
