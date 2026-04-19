"""Booking Agent for Phase 4 — Execution.

Handles the full booking workflow:
1. Add event to calendar
2. Create Google Doc
3. Attach Google Doc to calendar event
4. Email MF distributor
5. Log action to Google Sheets
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .config import get_gemini_actions_credentials
from .models import (
    ExecutionAction,
    ExecutionStatus,
    ExecutionResult,
    BookingExecutionRequest,
    CalendarEventDetails,
    GoogleDocDetails,
    EmailDetails,
    SheetsLogDetails,
)
from .google_workspace_mcp import get_workspace_mcp

logger = logging.getLogger(__name__)


class BookingAgent:
    """Agent that executes the booking workflow."""

    def __init__(self):
        self.workspace = get_workspace_mcp()
        self.credentials = get_gemini_actions_credentials()

    def execute_booking(self, request: BookingExecutionRequest) -> ExecutionResult:
        """Execute the full booking workflow.
        
        Args:
            request: The booking execution request.
            
        Returns:
            ExecutionResult with details of the execution.
        """
        logger.info(f"Starting booking execution for session {request.session_id}")
        
        # Initialize result tracking
        result = ExecutionResult(
            action=ExecutionAction.BOOK,
            status=ExecutionStatus.SUCCESS,
            message="",
        )
        
        try:
            # Step 1: Parse the time slot
            start_time = self._parse_time_slot(request.time_slot)
            end_time = start_time + timedelta(minutes=request.duration_minutes)
            
            # Step 2: Generate booking code
            booking_code = self.workspace.generate_booking_code()
            result.booking_code = booking_code
            
            # Step 3: Create calendar event
            try:
                calendar_details = self.workspace.create_calendar_event(
                    topic=request.topic,
                    start_time=start_time,
                    end_time=end_time,
                    booking_code=booking_code,
                    description=f"Appointment for {request.topic}. Booking Code: {booking_code}",
                )
                result.calendar_event = calendar_details
                logger.info(f"Created calendar event: {calendar_details.event_id}")
            except Exception as e:
                logger.error(f"Failed to create calendar event: {e}")
                result.status = ExecutionStatus.FAILED
                result.message = f"Failed to create calendar event: {str(e)}"
                result.error_details = {"step": "calendar_create", "error": str(e)}
                return result
            
            # Step 4: Create Google Doc
            try:
                doc_details = self.workspace.create_meeting_notes_doc(
                    topic=request.topic,
                    booking_code=booking_code,
                    meeting_time=request.time_slot,
                )
                result.google_doc = doc_details
                logger.info(f"Created Google Doc: {doc_details.doc_id}")
            except Exception as e:
                logger.error(f"Failed to create Google Doc: {e}")
                result.status = ExecutionStatus.PARTIAL
                result.error_details = {"step": "doc_create", "error": str(e)}
                # Continue with other steps
            
            # Step 5: Attach Google Doc to calendar event
            if result.google_doc and result.google_doc.doc_link and result.calendar_event:
                try:
                    success = self.workspace.update_calendar_event_with_doc(
                        event_id=result.calendar_event.event_id,
                        doc_link=result.google_doc.doc_link,
                    )
                    if success:
                        logger.info(f"Attached doc to calendar event")
                    else:
                        logger.warning(f"Could not attach doc to calendar event")
                except Exception as e:
                    logger.warning(f"Failed to attach doc to calendar event: {e}")
            
            # Step 6: Send email to MF distributor
            try:
                email_details = self.workspace.send_booking_confirmation_email(
                    topic=request.topic,
                    booking_code=booking_code,
                    meeting_time=request.time_slot,
                    doc_link=result.google_doc.doc_link if result.google_doc else None,
                    event_link=result.calendar_event.event_link if result.calendar_event else None,
                )
                result.email = email_details
                logger.info(f"Sent booking confirmation email: {email_details.message_id}")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                if result.status == ExecutionStatus.SUCCESS:
                    result.status = ExecutionStatus.PARTIAL
                if not result.error_details:
                    result.error_details = {}
                result.error_details["email_error"] = str(e)
            
            # Step 7: Log to Google Sheets
            try:
                slot_date = start_time.strftime("%Y-%m-%d")
                slot_time_str = start_time.strftime("%H:%M")
                
                sheets_details = self.workspace.log_to_sheets(
                    log_type="booking",
                    booking_code=booking_code,
                    slot_date=slot_date,
                    slot_time=slot_time_str,
                    doc_link=result.google_doc.doc_link if result.google_doc else None,
                )
                result.sheets_log = sheets_details
                logger.info(f"Logged to sheets: row {sheets_details.row_number}")
            except Exception as e:
                logger.error(f"Failed to log to sheets: {e}")
                if result.status == ExecutionStatus.SUCCESS:
                    result.status = ExecutionStatus.PARTIAL
                if not result.error_details:
                    result.error_details = {}
                result.error_details["sheets_error"] = str(e)
            
            # Build final message - always show success to user if calendar event was created
            # Internal errors (email, sheets, doc) are logged but not shown to user
            if result.calendar_event and result.calendar_event.event_id:
                result.status = ExecutionStatus.SUCCESS
                # Format booking code with spaces so TTS reads digits individually
                spoken_code = " ".join(list(booking_code))
                result.message = f"Booking successful. Your booking code is {spoken_code}."
            else:
                result.status = ExecutionStatus.FAILED
                result.message = f"Booking failed. Please try again."
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error during booking execution: {e}")
            result.status = ExecutionStatus.FAILED
            result.message = f"Booking failed due to an unexpected error: {str(e)}"
            result.error_details = {"step": "unknown", "error": str(e)}
            return result

    def _parse_time_slot(self, time_slot: str) -> datetime:
        """Parse a time slot string into a datetime object.
        
        Args:
            time_slot: Time slot string (ISO format or natural language).
            
        Returns:
            datetime object.
        """
        # Try ISO format first (preferred path)
        try:
            return datetime.fromisoformat(time_slot.replace("Z", "+00:00"))
        except ValueError:
            pass
        
        # Try common strftime formats
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%B %d, %Y %H:%M",
            "%b %d, %Y %H:%M",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_slot, fmt)
            except ValueError:
                continue
        
        # Fallback: use Phase 2's robust natural language parser
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from phase2_eligibility_check.eligibility_agent import EligibilityAgent
            agent = EligibilityAgent.__new__(EligibilityAgent)  # Skip __init__ (no LLM needed)
            start, _end = agent._parse_time_slot(time_slot)
            logger.info(f"Parsed time slot via Phase 2 fallback: {start.isoformat()}")
            return start
        except Exception as fallback_err:
            logger.error(f"Phase 2 fallback parsing also failed: {fallback_err}")
        
        # If all parsing fails, raise an error
        raise ValueError(f"Could not parse time slot: {time_slot}")


# Singleton instance
_booking_agent: Optional[BookingAgent] = None


def get_booking_agent() -> BookingAgent:
    """Get or create the Booking Agent singleton."""
    global _booking_agent
    if _booking_agent is None:
        _booking_agent = BookingAgent()
    return _booking_agent
