from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class EligibilityStatus(str, Enum):
    """Eligibility check result status."""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    ERROR = "error"


class CalendarEvent(BaseModel):
    """Represents a calendar event."""
    id: str
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None


class EligibilityResult(BaseModel):
    """Result of an eligibility check."""
    status: EligibilityStatus
    message: str
    requested_slot: Optional[str] = None
    topic: Optional[str] = None
    booking_code: Optional[str] = None
    conflicting_events: List[CalendarEvent] = Field(default_factory=list)
    knowledge_base_context: Optional[str] = None


class BookingEligibilityRequest(BaseModel):
    """Request to check booking eligibility."""
    topic: str
    time_slot: str
    session_id: str


class CancellationEligibilityRequest(BaseModel):
    """Request to check cancellation eligibility."""
    booking_code: str
    session_id: str


class EligibilityCheckResponse(BaseModel):
    """Response from eligibility check endpoint."""
    session_id: str
    status: EligibilityStatus
    message: str
    can_proceed: bool
    details: Optional[dict] = None
