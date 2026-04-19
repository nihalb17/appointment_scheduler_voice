"""Google Calendar MCP (Model Context Protocol) client.

Provides read/write operations for Google Calendar.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import get_google_credentials
from .models import CalendarEvent

logger = logging.getLogger(__name__)


class CalendarMCP:
    """Google Calendar MCP client for reading and writing calendar events."""

    def __init__(self):
        self.creds = None
        self.service = None
        self.calendar_id = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google using OAuth2 credentials."""
        google_creds = get_google_credentials()
        
        if not all([google_creds["client_id"], google_creds["client_secret"], google_creds["refresh_token"]]):
            logger.error("Google OAuth credentials not configured")
            raise ValueError("Google OAuth credentials not configured. Please check your .env file.")

        self.creds = Credentials(
            token=None,
            refresh_token=google_creds["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_creds["client_id"],
            client_secret=google_creds["client_secret"],
        )
        
        self.service = build("calendar", "v3", credentials=self.creds)
        self.calendar_id = google_creds["calendar_id"] or "primary"
        logger.info("Calendar MCP authenticated successfully")

    def read_calendar(
        self,
        time_min: datetime,
        time_max: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[CalendarEvent]:
        """Read events from the calendar within a time range.
        
        Args:
            time_min: Start time (inclusive)
            time_max: End time (exclusive). Defaults to time_min + 7 days.
            max_results: Maximum number of events to return.
            
        Returns:
            List of CalendarEvent objects.
        """
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        try:
            # Ensure timezone-aware datetimes for Google Calendar API
            from datetime import timezone
            
            if time_min.tzinfo is None:
                time_min = time_min.replace(tzinfo=timezone.utc)
            if time_max.tzinfo is None:
                time_max = time_max.replace(tzinfo=timezone.utc)
            
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            
            events = events_result.get("items", [])
            calendar_events = []
            
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                
                # Parse datetime strings
                if "T" in start:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                else:
                    # All-day event
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                
                calendar_events.append(
                    CalendarEvent(
                        id=event["id"],
                        summary=event.get("summary", "No title"),
                        start=start_dt,
                        end=end_dt,
                        description=event.get("description"),
                    )
                )
            
            logger.info(f"Retrieved {len(calendar_events)} events from calendar")
            return calendar_events
            
        except HttpError as e:
            logger.error(f"Failed to read calendar: {e}")
            raise

    def find_event_by_booking_code(self, booking_code: str) -> Optional[CalendarEvent]:
        """Find a calendar event by its booking code.
        
        Args:
            booking_code: The 4-digit booking code to search for.
            
        Returns:
            CalendarEvent if found, None otherwise.
        """
        try:
            # Use the official Google Calendar 'q' parameter for robust searching
            # across summary, description, and other fields.
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    q=booking_code,
                    maxResults=10,
                    singleEvents=True,
                )
                .execute()
            )
            
            events = events_result.get("items", [])
            
            # Double check that the matching code is truly present to avoid false positives
            for event in events:
                summary = event.get("summary", "")
                description = event.get("description", "")
                if booking_code in summary or (description and booking_code in description):
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))
                    
                    if "T" in start:
                        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    else:
                        start_dt = datetime.fromisoformat(start)
                        end_dt = datetime.fromisoformat(end)
                    
                    return CalendarEvent(
                        id=event["id"],
                        summary=summary,
                        start=start_dt,
                        end=end_dt,
                        description=description,
                    )
            
            return None
            
        except HttpError as e:
            logger.error(f"Failed to find event by booking code: {e}")
            return None

    def check_slot_availability(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[bool, List[CalendarEvent]]:
        """Check if a time slot is available.
        
        Args:
            start_time: Proposed start time.
            end_time: Proposed end time.
            
        Returns:
            Tuple of (is_available, conflicting_events).
        """
        # Get events that overlap with the proposed slot
        events = self.read_calendar(
            time_min=start_time - timedelta(hours=1),
            time_max=end_time + timedelta(hours=1),
        )
        
        conflicting_events = []
        
        for event in events:
            # Check for overlap
            if (event.start < end_time and event.end > start_time):
                conflicting_events.append(event)
        
        is_available = len(conflicting_events) == 0
        return is_available, conflicting_events


# Singleton instance
_calendar_mcp: Optional[CalendarMCP] = None


def get_calendar_mcp() -> CalendarMCP:
    """Get or create the Calendar MCP singleton."""
    global _calendar_mcp
    if _calendar_mcp is None:
        _calendar_mcp = CalendarMCP()
    return _calendar_mcp
