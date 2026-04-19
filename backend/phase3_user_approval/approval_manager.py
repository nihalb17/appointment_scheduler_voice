"""Approval Manager for Phase 3 — User Approval.

Manages user approval state and handles confirmation/rejection of booking
and cancellation requests before they proceed to Phase 4 (Execution).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from threading import Lock

from .models import (
    ApprovalState,
    ApprovalAction,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalConfirmation,
    ApprovalResponse,
    ApprovalSummary,
)
from .config import get_approval_settings

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages user approval state for booking and cancellation requests.
    
    This class handles:
    1. Creating approval requests after eligibility check passes
    2. Storing approval state per session
    3. Processing user confirmation/rejection
    4. Cleaning up expired approvals
    """
    
    def __init__(self):
        # In-memory store: session_id -> ApprovalState
        self._approvals: Dict[str, ApprovalState] = {}
        self._lock = Lock()
        self._settings = get_approval_settings()
        logger.info("Approval Manager initialized")
    
    def create_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """Create a new approval request after eligibility check passes.
        
        Args:
            request: The approval request with action details.
            
        Returns:
            ApprovalResponse with the created approval state.
        """
        with self._lock:
            # Check if there's already a pending approval for this session
            existing = self._approvals.get(request.session_id)
            if existing and existing.status == ApprovalStatus.PENDING:
                # Replace the existing pending approval
                logger.info(f"Replacing existing pending approval for session {request.session_id}")
            
            # Parse event_start if provided
            event_start = None
            if request.event_start:
                try:
                    event_start = datetime.fromisoformat(request.event_start.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Could not parse event_start: {request.event_start}")
            
            # Calculate expiry time
            expiry_minutes = self._settings["expiry_minutes"]
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            
            # Create the approval state
            approval_state = ApprovalState(
                session_id=request.session_id,
                action=request.action,
                status=ApprovalStatus.PENDING,
                topic=request.topic,
                time_slot=request.time_slot,
                booking_code=request.booking_code,
                event_summary=request.event_summary,
                event_start=event_start,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                eligibility_details=request.eligibility_details,
            )
            
            # Store the approval
            self._approvals[request.session_id] = approval_state
            
            logger.info(
                f"Created {request.action} approval for session {request.session_id}"
            )
            
            # Build the response
            summary = self._build_summary(approval_state)
            
            return ApprovalResponse(
                session_id=request.session_id,
                status=ApprovalStatus.PENDING,
                action=request.action,
                message=self._build_pending_message(approval_state),
                can_proceed_to_execution=False,
                summary=summary.dict(),
            )
    
    def process_confirmation(self, confirmation: ApprovalConfirmation) -> ApprovalResponse:
        """Process user confirmation or rejection.
        
        Args:
            confirmation: The user's decision (approve/reject).
            
        Returns:
            ApprovalResponse with the result.
        """
        with self._lock:
            session_id = confirmation.session_id
            
            # Check if there's a pending approval
            approval = self._approvals.get(session_id)
            if not approval:
                logger.warning(f"No pending approval found for session {session_id}")
                return ApprovalResponse(
                    session_id=session_id,
                    status=ApprovalStatus.REJECTED,
                    message="No pending approval found. Please start over.",
                    can_proceed_to_execution=False,
                )
            
            # Check if expired
            if approval.expires_at and datetime.utcnow() > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED
                logger.info(f"Approval expired for session {session_id}")
                return ApprovalResponse(
                    session_id=session_id,
                    status=ApprovalStatus.EXPIRED,
                    action=approval.action,
                    message="This approval request has expired. Please start over.",
                    can_proceed_to_execution=False,
                )
            
            # Process the decision
            decision = confirmation.decision.lower().strip()
            
            if decision in ["approve", "approved", "yes", "confirm", "proceed", "ok"]:
                approval.status = ApprovalStatus.APPROVED
                logger.info(f"Approval granted for session {session_id}")
                
                summary = self._build_summary(approval)
                
                return ApprovalResponse(
                    session_id=session_id,
                    status=ApprovalStatus.APPROVED,
                    action=approval.action,
                    message=self._build_approved_message(approval),
                    can_proceed_to_execution=True,
                    summary=summary.dict(),
                )
            
            elif decision in ["reject", "rejected", "no", "cancel", "decline", "deny"]:
                approval.status = ApprovalStatus.REJECTED
                logger.info(f"Approval rejected for session {session_id}")
                
                return ApprovalResponse(
                    session_id=session_id,
                    status=ApprovalStatus.REJECTED,
                    action=approval.action,
                    message=self._build_rejected_message(approval),
                    can_proceed_to_execution=False,
                )
            
            else:
                # Unknown decision
                logger.warning(f"Unknown decision '{decision}' for session {session_id}")
                return ApprovalResponse(
                    session_id=session_id,
                    status=ApprovalStatus.PENDING,
                    action=approval.action,
                    message="Please confirm with 'yes' to proceed or 'no' to cancel.",
                    can_proceed_to_execution=False,
                )
    
    def get_pending_approval(self, session_id: str) -> Optional[ApprovalState]:
        """Get the pending approval for a session if it exists.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The ApprovalState if pending, None otherwise.
        """
        with self._lock:
            approval = self._approvals.get(session_id)
            if approval and approval.status == ApprovalStatus.PENDING:
                # Check if expired
                if approval.expires_at and datetime.utcnow() > approval.expires_at:
                    approval.status = ApprovalStatus.EXPIRED
                    return None
                return approval
            return None
    
    def clear_approval(self, session_id: str) -> None:
        """Clear the approval state for a session.
        
        Args:
            session_id: The session ID to clear.
        """
        with self._lock:
            if session_id in self._approvals:
                del self._approvals[session_id]
                logger.debug(f"Cleared approval for session {session_id}")
    
    def cleanup_expired(self) -> int:
        """Clean up expired approval requests.
        
        Returns:
            Number of expired approvals removed.
        """
        with self._lock:
            now = datetime.utcnow()
            expired_sessions = [
                session_id
                for session_id, approval in self._approvals.items()
                if approval.expires_at and now > approval.expires_at
                and approval.status == ApprovalStatus.PENDING
            ]
            
            for session_id in expired_sessions:
                self._approvals[session_id].status = ApprovalStatus.EXPIRED
                logger.info(f"Marked approval as expired for session {session_id}")
            
            return len(expired_sessions)
    
    def _build_summary(self, approval: ApprovalState) -> ApprovalSummary:
        """Build an approval summary for display to the user."""
        if approval.action == ApprovalAction.BOOK:
            return ApprovalSummary.for_booking(
                topic=approval.topic or "Unknown",
                time_slot=approval.time_slot or "Unknown",
            )
        else:  # CANCEL
            return ApprovalSummary.for_cancellation(
                booking_code=approval.booking_code or "Unknown",
                event_summary=approval.event_summary,
            )
    
    def _build_pending_message(self, approval: ApprovalState) -> str:
        """Build the message shown when approval is pending."""
        if approval.action == ApprovalAction.BOOK:
            return (
                f"Please confirm: Book a {approval.topic} appointment "
                f"at {approval.time_slot}."
            )
        else:  # CANCEL
            if approval.event_summary:
                return (
                    f"Please confirm: Cancel appointment '{approval.event_summary}' "
                    f"with booking code {approval.booking_code}."
                )
            return (
                f"Please confirm: Cancel appointment with booking code "
                f"{approval.booking_code}."
            )
    
    def _build_approved_message(self, approval: ApprovalState) -> str:
        """Build the message shown when approval is granted."""
        if approval.action == ApprovalAction.BOOK:
            return (
                f"Confirmed. Proceeding to book your {approval.topic} appointment "
                f"at {approval.time_slot}."
            )
        else:  # CANCEL
            return (
                f"Confirmed. Proceeding to cancel appointment with booking code "
                f"{approval.booking_code}."
            )
    
    def _build_rejected_message(self, approval: ApprovalState) -> str:
        """Build the message shown when approval is rejected."""
        if approval.action == ApprovalAction.BOOK:
            return (
                f"Booking cancelled. If you'd like to book a different time, "
                f"please let me know."
            )
        else:  # CANCEL
            return (
                f"Cancellation cancelled. Your appointment with booking code "
                f"{approval.booking_code} remains scheduled."
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about current approvals."""
        with self._lock:
            stats = {
                "total": len(self._approvals),
                "pending": sum(
                    1 for a in self._approvals.values()
                    if a.status == ApprovalStatus.PENDING
                ),
                "approved": sum(
                    1 for a in self._approvals.values()
                    if a.status == ApprovalStatus.APPROVED
                ),
                "rejected": sum(
                    1 for a in self._approvals.values()
                    if a.status == ApprovalStatus.REJECTED
                ),
                "expired": sum(
                    1 for a in self._approvals.values()
                    if a.status == ApprovalStatus.EXPIRED
                ),
            }
            return stats


# Singleton instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get or create the Approval Manager singleton."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


# Convenience functions for direct use
def create_approval(request: ApprovalRequest) -> ApprovalResponse:
    """Create a new approval request."""
    return get_approval_manager().create_approval(request)


def process_confirmation(confirmation: ApprovalConfirmation) -> ApprovalResponse:
    """Process a user confirmation/rejection."""
    return get_approval_manager().process_confirmation(confirmation)


def get_pending_approval(session_id: str) -> Optional[ApprovalState]:
    """Get pending approval for a session."""
    return get_approval_manager().get_pending_approval(session_id)


def clear_approval(session_id: str) -> None:
    """Clear approval for a session."""
    return get_approval_manager().clear_approval(session_id)
