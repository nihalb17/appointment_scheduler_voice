"""Models for Phase 5 — Confirmation.

Defines data structures for confirmation messages sent to the user after execution.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ConfirmationAction(str, Enum):
    """Type of confirmed action."""
    BOOK = "book"
    CANCEL = "cancel"


class ConfirmationStatus(str, Enum):
    """Whether the action was successfully completed."""
    SUCCESS = "success"
    FAILED = "failed"


class ConfirmationRequest(BaseModel):
    """Request to build a confirmation message from execution results."""
    session_id: str
    action: ConfirmationAction
    success: bool
    user_message: str  # The user-facing message from Phase 4
    booking_code: Optional[str] = None
    event_link: Optional[str] = None
    doc_link: Optional[str] = None
    scheduled_time: Optional[str] = None  # ISO format


class ConfirmationResponse(BaseModel):
    """Response containing the final confirmation details for the frontend."""
    session_id: str
    action: ConfirmationAction
    status: ConfirmationStatus
    confirmed: bool
    user_message: str
    banner_text: str  # Short text for the confirmation banner
    booking_code: Optional[str] = None
    event_link: Optional[str] = None
    doc_link: Optional[str] = None
    close_chat: bool = False  # Signal frontend to close the chat input
