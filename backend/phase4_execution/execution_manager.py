"""Execution Manager for Phase 4 — Execution.

Orchestrates the Booking and Cancellation agents and provides a unified interface
for executing approved actions.
"""

import logging
from typing import Optional, Dict, Any

from .models import (
    ExecutionAction,
    ExecutionStatus,
    ExecutionResult,
    ExecutionResponse,
    BookingExecutionRequest,
    CancellationExecutionRequest,
)
from .booking_agent import get_booking_agent
from .cancellation_agent import get_cancellation_agent

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Manages the execution of approved booking and cancellation requests.
    
    This class provides a unified interface for:
    1. Executing bookings after user approval
    2. Executing cancellations after user approval
    3. Building user-friendly response messages
    """

    def __init__(self):
        self.booking_agent = get_booking_agent()
        self.cancellation_agent = get_cancellation_agent()

    def execute_booking(self, request: BookingExecutionRequest) -> ExecutionResponse:
        """Execute a booking after user approval.
        
        Args:
            request: The booking execution request.
            
        Returns:
            ExecutionResponse with the result and user-friendly message.
        """
        logger.info(f"ExecutionManager: Executing booking for session {request.session_id}")
        
        try:
            result = self.booking_agent.execute_booking(request)
            return self._build_response(request.session_id, result)
        except Exception as e:
            logger.error(f"ExecutionManager: Booking execution failed: {e}")
            return ExecutionResponse(
                session_id=request.session_id,
                action=ExecutionAction.BOOK,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Booking failed: {str(e)}",
                user_message="I'm sorry, but I couldn't complete your booking due to a technical issue. Please try again.",
                error=str(e),
            )

    def execute_cancellation(self, request: CancellationExecutionRequest) -> ExecutionResponse:
        """Execute a cancellation after user approval.
        
        Args:
            request: The cancellation execution request.
            
        Returns:
            ExecutionResponse with the result and user-friendly message.
        """
        logger.info(f"ExecutionManager: Executing cancellation for session {request.session_id}")
        
        try:
            result = self.cancellation_agent.execute_cancellation(request)
            return self._build_response(request.session_id, result)
        except Exception as e:
            logger.error(f"ExecutionManager: Cancellation execution failed: {e}")
            return ExecutionResponse(
                session_id=request.session_id,
                action=ExecutionAction.CANCEL,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Cancellation failed: {str(e)}",
                user_message="I'm sorry, but I couldn't complete the cancellation due to a technical issue. Please try again.",
                error=str(e),
            )

    def _build_response(self, session_id: str, result: ExecutionResult) -> ExecutionResponse:
        """Build an execution response from the result.
        
        Args:
            session_id: The session ID.
            result: The execution result.
            
        Returns:
            ExecutionResponse with user-friendly messaging.
        """
        success = result.status == ExecutionStatus.SUCCESS
        
        if result.action == ExecutionAction.BOOK:
            user_message = self._build_booking_user_message(result)
        else:
            user_message = self._build_cancellation_user_message(result)
        
        return ExecutionResponse(
            session_id=session_id,
            action=result.action,
            status=result.status,
            success=success,
            message=result.message,
            user_message=user_message,
            result=result,
        )

    def _build_booking_user_message(self, result: ExecutionResult) -> str:
        """Build a user-friendly message for a booking result.
        
        Args:
            result: The execution result.
            
        Returns:
            User-friendly message string.
        """
        # Always show success message if calendar event was created
        # Don't mention partial failures or technical issues to the user
        if result.status == ExecutionStatus.SUCCESS or (result.calendar_event and result.calendar_event.event_id):
            lines = [
                f"Your appointment has been successfully booked!",
                f"",
                f"Booking Code: {result.booking_code}",
            ]
            
            if result.calendar_event and result.calendar_event.start_time:
                lines.append(f"Date: {result.calendar_event.start_time.strftime('%B %d, %Y')}")
                lines.append(f"Time: {result.calendar_event.start_time.strftime('%I:%M %p')}")
            
            return "\n".join(lines)
        
        else:  # FAILED
            return f"I'm sorry, but I couldn't complete your booking. Please try again."

    def _build_cancellation_user_message(self, result: ExecutionResult) -> str:
        """Build a user-friendly message for a cancellation result.
        
        Args:
            result: The execution result.
            
        Returns:
            User-friendly message string.
        """
        # Always show success message if calendar event was deleted
        # Don't mention partial failures or technical issues to the user
        if result.status == ExecutionStatus.SUCCESS or (result.calendar_event and result.calendar_event.event_id):
            lines = [
                f"Your appointment has been successfully cancelled.",
                f"",
                f"Booking Code: {result.booking_code}",
            ]
            
            if result.calendar_event and result.calendar_event.start_time:
                lines.append(f"Was scheduled for: {result.calendar_event.start_time.strftime('%B %d, %Y at %I:%M %p')}")
            
            return "\n".join(lines)
        
        else:  # FAILED
            # Check if it's the specific "not found" error
            if result.error_details and result.error_details.get("step") == "find_event":
                return f"There is no event with code {result.booking_code}"
            return f"I'm sorry, but I couldn't complete the cancellation. Please try again."


# Singleton instance
_execution_manager: Optional[ExecutionManager] = None


def get_execution_manager() -> ExecutionManager:
    """Get or create the Execution Manager singleton."""
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = ExecutionManager()
    return _execution_manager


# Convenience functions for direct use
def execute_booking(request: BookingExecutionRequest) -> ExecutionResponse:
    """Execute a booking request."""
    return get_execution_manager().execute_booking(request)


def execute_cancellation(request: CancellationExecutionRequest) -> ExecutionResponse:
    """Execute a cancellation request."""
    return get_execution_manager().execute_cancellation(request)
