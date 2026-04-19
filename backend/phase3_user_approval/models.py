"""Models for Phase 3 — User Approval.

Defines data structures for managing user approval state and requests.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ApprovalAction(str, Enum):
    """Type of action awaiting user approval."""
    BOOK = "book"
    CANCEL = "cancel"


class ApprovalStatus(str, Enum):
    """Status of the approval request."""
    PENDING = "pending"      # Awaiting user confirmation
    APPROVED = "approved"    # User confirmed, ready for execution
    REJECTED = "rejected"    # User declined
    EXPIRED = "expired"      # Approval request timed out


class ApprovalState(BaseModel):
    """Represents the current approval state for a session.
    
    This is stored in-memory and tracks what action is awaiting approval.
    """
    session_id: str
    action: ApprovalAction
    status: ApprovalStatus
    
    # Booking-specific fields
    topic: Optional[str] = None
    time_slot: Optional[str] = None
    
    # Cancellation-specific fields
    booking_code: Optional[str] = None
    event_summary: Optional[str] = None
    event_start: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Additional context from eligibility check
    eligibility_details: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    """Request to create a new approval (called after eligibility check passes)."""
    session_id: str
    action: ApprovalAction
    topic: Optional[str] = None
    time_slot: Optional[str] = None
    booking_code: Optional[str] = None
    event_summary: Optional[str] = None
    event_start: Optional[str] = None  # ISO format
    eligibility_details: Optional[Dict[str, Any]] = None


class ApprovalConfirmation(BaseModel):
    """Request to confirm or reject a pending approval."""
    session_id: str
    decision: str  # "approve" or "reject"


class ApprovalResponse(BaseModel):
    """Response from approval operations."""
    session_id: str
    status: ApprovalStatus
    action: Optional[ApprovalAction] = None
    message: str
    can_proceed_to_execution: bool = False
    
    # Summary of what was approved/rejected
    summary: Optional[Dict[str, Any]] = None


class ApprovalSummary(BaseModel):
    """Summary of the action awaiting approval (shown to user)."""
    action: ApprovalAction
    title: str
    details: list[str]
    
    @classmethod
    def for_booking(cls, topic: str, time_slot: str) -> "ApprovalSummary":
        """Create a summary for a booking approval."""
        return cls(
            action=ApprovalAction.BOOK,
            title="Confirm Booking",
            details=[
                f"Topic: {topic}",
                f"Time: {time_slot}",
            ],
        )
    
    @classmethod
    def for_cancellation(cls, booking_code: str, event_summary: Optional[str] = None) -> "ApprovalSummary":
        """Create a summary for a cancellation approval."""
        details = [f"Booking Code: {booking_code}"]
        if event_summary:
            details.append(f"Event: {event_summary}")
        
        return cls(
            action=ApprovalAction.CANCEL,
            title="Confirm Cancellation",
            details=details,
        )
