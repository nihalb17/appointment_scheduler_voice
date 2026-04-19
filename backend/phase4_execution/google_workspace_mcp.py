"""Google Workspace MCP (Model Context Protocol) client.

Provides unified access to Google Calendar, Docs, Gmail, and Sheets.
"""

import logging
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import (
    get_google_credentials,
    get_google_docs_config,
    get_gmail_config,
    get_google_sheets_config,
)
from .models import (
    CalendarEventDetails,
    GoogleDocDetails,
    EmailDetails,
    SheetsLogDetails,
)

logger = logging.getLogger(__name__)


class GoogleWorkspaceMCP:
    """Unified Google Workspace MCP client for Calendar, Docs, Gmail, and Sheets."""

    def __init__(self):
        self.creds = None
        self.calendar_service = None
        self.docs_service = None
        self.gmail_service = None
        self.sheets_service = None
        self.drive_service = None
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
        
        self.calendar_service = build("calendar", "v3", credentials=self.creds)
        self.docs_service = build("docs", "v1", credentials=self.creds)
        self.gmail_service = build("gmail", "v1", credentials=self.creds)
        self.sheets_service = build("sheets", "v4", credentials=self.creds)
        self.drive_service = build("drive", "v3", credentials=self.creds)
        
        self.calendar_id = google_creds["calendar_id"] or "primary"
        logger.info("Google Workspace MCP authenticated successfully")

    def generate_booking_code(self) -> str:
        """Generate a unique 4-digit booking code."""
        return ''.join(random.choices(string.digits, k=4))

    # ==================== Calendar Operations ====================

    def create_calendar_event(
        self,
        topic: str,
        start_time: datetime,
        end_time: datetime,
        booking_code: str,
        description: Optional[str] = None,
    ) -> CalendarEventDetails:
        """Create a calendar event for a booking.
        
        Args:
            topic: The appointment topic.
            start_time: Event start time.
            end_time: Event end time.
            booking_code: The unique booking code.
            description: Optional event description.
            
        Returns:
            CalendarEventDetails with event information.
        """
        summary = f"{topic} — Booking Code: {booking_code}"
        
        event_body = {
            "summary": summary,
            "description": description or f"Appointment for {topic}. Booking Code: {booking_code}",
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }
        
        try:
            event = self.calendar_service.events().insert(
                calendarId=self.calendar_id,
                body=event_body,
            ).execute()
            
            logger.info(f"Created calendar event: {event['id']} for booking {booking_code}")
            
            return CalendarEventDetails(
                event_id=event["id"],
                event_link=event.get("htmlLink"),
                summary=summary,
                start_time=start_time,
                end_time=end_time,
            )
        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise

    def update_calendar_event_with_doc(
        self,
        event_id: str,
        doc_link: str,
    ) -> bool:
        """Update a calendar event to attach a Google Doc.
        
        Args:
            event_id: The calendar event ID.
            doc_link: The Google Doc link to attach.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # First, get the current event
            event = self.calendar_service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute()
            
            # Update the description with the doc link
            current_description = event.get("description", "")
            updated_description = f"{current_description}\n\nMeeting Notes: {doc_link}"
            
            event["description"] = updated_description
            
            # Update the event
            updated_event = self.calendar_service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event,
            ).execute()
            
            logger.info(f"Updated calendar event {event_id} with doc link: {doc_link}")
            return True
        except HttpError as e:
            logger.error(f"Failed to update calendar event with doc: {e}")
            return False

    def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event.
        
        Args:
            event_id: The calendar event ID to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.calendar_service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute()
            
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False

    def find_event_by_booking_code(self, booking_code: str) -> Optional[CalendarEventDetails]:
        """Find a calendar event by its booking code.
        
        Args:
            booking_code: The 4-digit booking code to search for.
            
        Returns:
            CalendarEventDetails if found, None otherwise.
        """
        time_min = datetime.utcnow() - timedelta(days=90)
        time_max = datetime.utcnow() + timedelta(days=90)
        
        # Ensure timezone-aware datetimes
        from datetime import timezone
        if time_min.tzinfo is None:
            time_min = time_min.replace(tzinfo=timezone.utc)
        if time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=timezone.utc)
        
        try:
            events_result = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = events_result.get("items", [])
            
            for event in events:
                summary = event.get("summary", "")
                description = event.get("description", "")
                
                if booking_code in summary or booking_code in description:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))
                    
                    if "T" in start:
                        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    else:
                        start_dt = datetime.fromisoformat(start)
                        end_dt = datetime.fromisoformat(end)
                    
                    return CalendarEventDetails(
                        event_id=event["id"],
                        event_link=event.get("htmlLink"),
                        summary=summary,
                        start_time=start_dt,
                        end_time=end_dt,
                    )
            
            return None
        except HttpError as e:
            logger.error(f"Failed to find event by booking code: {e}")
            return None

    # ==================== Google Docs Operations ====================

    def create_meeting_notes_doc(
        self,
        topic: str,
        booking_code: str,
        meeting_time: Optional[str] = None,
    ) -> GoogleDocDetails:
        """Create a Google Doc for meeting notes.
        
        Args:
            topic: The appointment topic.
            booking_code: The unique booking code.
            meeting_time: Optional meeting time string.
            
        Returns:
            GoogleDocDetails with document information.
        """
        title = f"{topic} — {booking_code}"
        docs_config = get_google_docs_config()
        
        # Create the document
        doc_body = {
            "title": title,
        }
        
        try:
            doc = self.docs_service.documents().create(body=doc_body).execute()
            doc_id = doc["documentId"]
            doc_link = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            # Add initial content
            content = f"Meeting Notes\n\n"
            content += f"Topic: {topic}\n"
            content += f"Booking Code: {booking_code}\n"
            if meeting_time:
                content += f"Scheduled Time: {meeting_time}\n"
            content += f"\n---\n\n"
            content += "Agenda:\n\n"
            content += "Notes:\n\n"
            content += "Action Items:\n\n"
            
            # Insert content into the document
            requests = [
                {
                    "insertText": {
                        "location": {
                            "index": 1,
                        },
                        "text": content,
                    }
                }
            ]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests},
            ).execute()
            
            # Move to specified folder if configured
            if docs_config.get("folder_id"):
                try:
                    self.drive_service.files().update(
                        fileId=doc_id,
                        addParents=docs_config["folder_id"],
                        fields="id, parents",
                    ).execute()
                except HttpError as e:
                    logger.warning(f"Could not move doc to folder: {e}")
            
            logger.info(f"Created Google Doc: {doc_id} for booking {booking_code}")
            
            return GoogleDocDetails(
                doc_id=doc_id,
                doc_link=doc_link,
                title=title,
            )
        except HttpError as e:
            logger.error(f"Failed to create Google Doc: {e}")
            raise

    # ==================== Gmail Operations ====================

    def send_booking_confirmation_email(
        self,
        topic: str,
        booking_code: str,
        meeting_time: str,
        doc_link: Optional[str] = None,
        event_link: Optional[str] = None,
    ) -> EmailDetails:
        """Send a booking confirmation email to the MF distributor.
        
        Args:
            topic: The appointment topic.
            booking_code: The unique booking code.
            meeting_time: The scheduled meeting time.
            doc_link: Optional Google Doc link.
            event_link: Optional calendar event link.
            
        Returns:
            EmailDetails with email information.
        """
        gmail_config = get_gmail_config()
        recipient = gmail_config.get("recipient_email")
        
        if not recipient:
            raise ValueError("MF_DISTRIBUTOR_EMAIL not configured")
        
        subject = f"New Booking Confirmed — {topic} ({booking_code})"
        
        # Build email body
        body_lines = [
            f"A new appointment has been booked.",
            f"",
            f"Topic: {topic}",
            f"Booking Code: {booking_code}",
            f"Scheduled Time: {meeting_time}",
        ]
        
        if doc_link:
            body_lines.extend([
                f"",
                f"Meeting Notes Document: {doc_link}",
            ])
        
        if event_link:
            body_lines.extend([
                f"",
                f"Calendar Event: {event_link}",
            ])
        
        body_lines.extend([
            f"",
            f"---",
            f"This is an automated message from the Appointment Scheduler.",
        ])
        
        body = "\n".join(body_lines)
        
        return self._send_email(recipient, subject, body)

    def send_cancellation_email(
        self,
        booking_code: str,
        event_summary: Optional[str] = None,
        meeting_time: Optional[str] = None,
    ) -> EmailDetails:
        """Send a cancellation notification email to the MF distributor.
        
        Args:
            booking_code: The booking code that was cancelled.
            event_summary: Optional event summary/topic.
            meeting_time: Optional meeting time.
            
        Returns:
            EmailDetails with email information.
        """
        gmail_config = get_gmail_config()
        recipient = gmail_config.get("recipient_email")
        
        if not recipient:
            raise ValueError("MF_DISTRIBUTOR_EMAIL not configured")
        
        subject = f"Booking Cancelled — {booking_code}"
        
        # Build email body
        body_lines = [
            f"An appointment has been cancelled.",
            f"",
            f"Booking Code: {booking_code}",
        ]
        
        if event_summary:
            body_lines.append(f"Event: {event_summary}")
        
        if meeting_time:
            body_lines.append(f"Scheduled Time: {meeting_time}")
        
        body_lines.extend([
            f"",
            f"---",
            f"This is an automated message from the Appointment Scheduler.",
        ])
        
        body = "\n".join(body_lines)
        
        return self._send_email(recipient, subject, body)

    def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> EmailDetails:
        """Send an email via Gmail API.
        
        Args:
            recipient: The recipient email address.
            subject: The email subject.
            body: The email body (plain text).
            
        Returns:
            EmailDetails with email information.
        """
        from email.mime.text import MIMEText
        import base64
        
        try:
            message = MIMEText(body, "plain", "utf-8")
            message["to"] = recipient
            message["subject"] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            send_result = self.gmail_service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()
            
            logger.info(f"Sent email: {send_result['id']} to {recipient}")
            
            return EmailDetails(
                message_id=send_result["id"],
                recipient=recipient,
                subject=subject,
            )
        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            raise

    # ==================== Google Sheets Operations ====================

    def log_to_sheets(
        self,
        log_type: str,  # "booking" or "cancellation"
        booking_code: str,
        slot_date: str,
        slot_time: str,
        doc_link: Optional[str] = None,
    ) -> SheetsLogDetails:
        """Log a booking or cancellation to Google Sheets.
        
        Args:
            log_type: Either "booking" or "cancellation".
            booking_code: The booking code.
            slot_date: The date of the slot.
            slot_time: The time of the slot.
            doc_link: Optional Google Doc link (only for bookings).
            
        Returns:
            SheetsLogDetails with log information.
        """
        sheets_config = get_google_sheets_config()
        spreadsheet_id = sheets_config.get("spreadsheet_id")
        sheet_name = sheets_config.get("sheet_name", "Meetings Log")
        
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SPREADSHEET_ID not configured")
        
        # Current timestamp
        updated_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Prepare row data
        row_data = [
            updated_time,
            log_type,
            booking_code,
            slot_date,
            slot_time,
            doc_link if doc_link else "",  # Empty for cancellations
        ]
        
        try:
            # Append the row to the sheet
            # Use proper quoting for sheet names with spaces
            range_notation = f"'{sheet_name}'!A:F" if ' ' in sheet_name else f"{sheet_name}!A:F"
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_data]},
            ).execute()
            
            row_number = result.get("updates", {}).get("updatedRange", "").split("!")[-1].split(":")[0]
            
            logger.info(f"Logged {log_type} to sheets: row {row_number}")
            
            return SheetsLogDetails(
                row_number=result.get("updates", {}).get("updatedRows", 0),
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
            )
        except HttpError as e:
            logger.error(f"Failed to log to sheets: {e}")
            raise


# Singleton instance
_workspace_mcp: Optional[GoogleWorkspaceMCP] = None


def get_workspace_mcp() -> GoogleWorkspaceMCP:
    """Get or create the Google Workspace MCP singleton."""
    global _workspace_mcp
    if _workspace_mcp is None:
        _workspace_mcp = GoogleWorkspaceMCP()
    return _workspace_mcp
