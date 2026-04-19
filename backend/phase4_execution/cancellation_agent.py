"""Cancellation Agent for Phase 4 — Execution.

Handles the full cancellation workflow:
1. Remove event from calendar
2. Email MF distributor
3. Log action to Google Sheets
"""

import logging
from datetime import datetime
from typing import Optional

from .config import get_gemini_actions_credentials
from .models import (
    ExecutionAction,
    ExecutionStatus,
    ExecutionResult,
    CancellationExecutionRequest,
    CalendarEventDetails,
    EmailDetails,
    SheetsLogDetails,
)
from .google_workspace_mcp import get_workspace_mcp

logger = logging.getLogger(__name__)


class CancellationAgent:
    """Agent that executes the cancellation workflow."""

    def __init__(self):
        self.workspace = get_workspace_mcp()
        self.credentials = get_gemini_actions_credentials()

    def execute_cancellation(self, request: CancellationExecutionRequest) -> ExecutionResult:
        """Execute the full cancellation workflow.
        
        Args:
            request: The cancellation execution request.
            
        Returns:
            ExecutionResult with details of the execution.
        """
        logger.info(f"Starting cancellation execution for session {request.session_id}")
        
        # Initialize result tracking
        result = ExecutionResult(
            action=ExecutionAction.CANCEL,
            status=ExecutionStatus.SUCCESS,
            booking_code=request.booking_code,
            message="",
        )
        
        try:
            # Step 1: Find the event by booking code
            event_details = None
            
            if request.event_id:
                # If we already have the event ID from eligibility check
                # We still need to get the event details for logging
                try:
                    # Try to find by booking code to get full details
                    event_details = self.workspace.find_event_by_booking_code(request.booking_code)
                except Exception as e:
                    logger.warning(f"Could not find event details: {e}")
            
            if not event_details:
                event_details = self.workspace.find_event_by_booking_code(request.booking_code)
            
            if not event_details:
                logger.error(f"Event not found for booking code: {request.booking_code}")
                result.status = ExecutionStatus.FAILED
                result.message = f"There is no event with code {request.booking_code}"
                result.error_details = {"step": "find_event", "error": "Event not found"}
                return result
            
            # Store event details before deletion for logging
            result.calendar_event = CalendarEventDetails(
                event_id=event_details.event_id,
                summary=event_details.summary,
                start_time=event_details.start_time,
                end_time=event_details.end_time,
            )
            
            # Extract slot date and time for logging
            slot_date = ""
            slot_time = ""
            if event_details.start_time:
                slot_date = event_details.start_time.strftime("%Y-%m-%d")
                slot_time = event_details.start_time.strftime("%H:%M")
            
            event_summary = event_details.summary or request.event_summary or "Unknown"
            meeting_time_str = ""
            if event_details.start_time:
                meeting_time_str = event_details.start_time.strftime("%Y-%m-%d %H:%M")
            
            # Step 2: Delete the calendar event
            try:
                success = self.workspace.delete_calendar_event(event_details.event_id)
                if success:
                    logger.info(f"Deleted calendar event: {event_details.event_id}")
                else:
                    logger.error(f"Failed to delete calendar event: {event_details.event_id}")
                    result.status = ExecutionStatus.FAILED
                    result.message = f"Failed to cancel the appointment. Please try again."
                    result.error_details = {"step": "calendar_delete", "error": "Delete failed"}
                    return result
            except Exception as e:
                logger.error(f"Failed to delete calendar event: {e}")
                result.status = ExecutionStatus.FAILED
                result.message = f"Failed to cancel the appointment: {str(e)}"
                result.error_details = {"step": "calendar_delete", "error": str(e)}
                return result
            
            # Step 3: Send cancellation email to MF distributor
            try:
                email_details = self.workspace.send_cancellation_email(
                    booking_code=request.booking_code,
                    event_summary=event_summary,
                    meeting_time=meeting_time_str if meeting_time_str else None,
                )
                result.email = email_details
                logger.info(f"Sent cancellation email: {email_details.message_id}")
            except Exception as e:
                logger.error(f"Failed to send cancellation email: {e}")
                result.status = ExecutionStatus.PARTIAL
                if not result.error_details:
                    result.error_details = {}
                result.error_details["email_error"] = str(e)
            
            # Step 4: Log to Google Sheets
            try:
                sheets_details = self.workspace.log_to_sheets(
                    log_type="cancellation",
                    booking_code=request.booking_code,
                    slot_date=slot_date,
                    slot_time=slot_time,
                    doc_link=None,  # No doc link for cancellations
                )
                result.sheets_log = sheets_details
                logger.info(f"Logged cancellation to sheets: row {sheets_details.row_number}")
            except Exception as e:
                logger.error(f"Failed to log cancellation to sheets: {e}")
                if result.status == ExecutionStatus.SUCCESS:
                    result.status = ExecutionStatus.PARTIAL
                if not result.error_details:
                    result.error_details = {}
                result.error_details["sheets_error"] = str(e)
            
            # Build final message - always show success to user if calendar event was deleted
            # Internal errors (email, sheets) are logged but not shown to user
            if result.calendar_event and result.calendar_event.event_id:
                result.status = ExecutionStatus.SUCCESS
                result.message = f"Cancellation successful. Appointment with code {request.booking_code} has been cancelled."
            else:
                result.status = ExecutionStatus.FAILED
                result.message = f"Cancellation failed. Please try again."
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error during cancellation execution: {e}")
            result.status = ExecutionStatus.FAILED
            result.message = f"Cancellation failed due to an unexpected error: {str(e)}"
            result.error_details = {"step": "unknown", "error": str(e)}
            return result


# Singleton instance
_cancellation_agent: Optional[CancellationAgent] = None


def get_cancellation_agent() -> CancellationAgent:
    """Get or create the Cancellation Agent singleton."""
    global _cancellation_agent
    if _cancellation_agent is None:
        _cancellation_agent = CancellationAgent()
    return _cancellation_agent
