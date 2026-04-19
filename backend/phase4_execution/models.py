"""Models for Phase 4 — Execution Agent.

Defines data structures for booking and cancellation execution requests and responses.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionAction(str, Enum):
    """Type of execution action."""
    BOOK = "book"
    CANCEL = "cancel"


class ExecutionStatus(str, Enum):
    """Status of the execution."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded, some failed


class CalendarEventDetails(BaseModel):
    """Details of a created or deleted calendar event."""
    event_id: Optional[str] = None
    event_link: Optional[str] = None
    summary: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class GoogleDocDetails(BaseModel):
    """Details of a created Google Doc."""
    doc_id: Optional[str] = None
    doc_link: Optional[str] = None
    title: Optional[str] = None


class EmailDetails(BaseModel):
    """Details of a sent email."""
    message_id: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None


class SheetsLogDetails(BaseModel):
    """Details of a logged entry in Google Sheets."""
    row_number: Optional[int] = None
    spreadsheet_id: Optional[str] = None
    sheet_name: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of an execution (booking or cancellation)."""
    action: ExecutionAction
    status: ExecutionStatus
    booking_code: Optional[str] = None
    message: str
    
    # Step-by-step results
    calendar_event: Optional[CalendarEventDetails] = None
    google_doc: Optional[GoogleDocDetails] = None
    email: Optional[EmailDetails] = None
    sheets_log: Optional[SheetsLogDetails] = None
    
    # Error details if any step failed
    error_details: Optional[Dict[str, Any]] = None
    
    # Timestamp
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class BookingExecutionRequest(BaseModel):
    """Request to execute a booking after user approval."""
    session_id: str
    topic: str
    time_slot: str  # ISO format datetime string
    duration_minutes: int = Field(default=30, ge=15, le=120)
    
    # Optional context from eligibility check
    eligibility_details: Optional[Dict[str, Any]] = None


class CancellationExecutionRequest(BaseModel):
    """Request to execute a cancellation after user approval."""
    session_id: str
    booking_code: str
    event_id: Optional[str] = None  # If known from eligibility check
    event_summary: Optional[str] = None
    event_start: Optional[str] = None  # ISO format
    
    # Optional context from eligibility check
    eligibility_details: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    """Response from execution operations."""
    session_id: str
    action: ExecutionAction
    status: ExecutionStatus
    success: bool
    message: str
    
    # Human-friendly summary for user
    user_message: str
    
    # Full execution result
    result: Optional[ExecutionResult] = None
    
    # Error information
    error: Optional[str] = None
