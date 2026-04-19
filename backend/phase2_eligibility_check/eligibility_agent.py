"""Eligibility Agent for Phase 2.

Uses Gemini LLM to check eligibility for booking and cancellation requests
using Calendar Read MCP protocol and RAG-based knowledge base context.
"""

import asyncio
import concurrent.futures
import csv
import json
import logging
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Set

import google.generativeai as genai

from .config import get_gemini_eligibility_credentials
from .models import EligibilityResult, EligibilityStatus, CalendarEvent
from .mcp_server import get_mcp_server

logger = logging.getLogger(__name__)

# Cache for holidays
_holidays: Optional[Set[str]] = None

def _load_holidays() -> Set[str]:
    """Load holidays from CSV file. Returns set of dates in YYYY-MM-DD format."""
    global _holidays
    if _holidays is not None:
        return _holidays
    
    _holidays = set()
    # Look for holiday CSV in common locations
    possible_paths = [
        Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "National Holidays List - Sheet1.csv",
        Path(__file__).resolve().parent.parent / "knowledge_base" / "National Holidays List - Sheet1.csv",
        Path("knowledge_base") / "National Holidays List - Sheet1.csv",
    ]
    
    for csv_path in possible_paths:
        if csv_path.exists():
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        date_str = row.get('Date(DD/MM/YYYY)', '')
                        if date_str:
                            # Parse DD/MM/YYYY format
                            day, month, year = date_str.split('/')
                            # Convert to YYYY-MM-DD format
                            formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            _holidays.add(formatted_date)
                logger.info(f"Loaded {len(_holidays)} holidays from {csv_path}")
                break
            except Exception as e:
                logger.warning(f"Failed to load holidays from {csv_path}: {e}")
    
    return _holidays

def is_holiday(date: datetime) -> bool:
    """Check if a date is a holiday."""
    holidays = _load_holidays()
    date_str = date.strftime('%Y-%m-%d')
    return date_str in holidays

# Eligibility Agent System Prompt with MCP tools
ELIGIBILITY_SYSTEM_PROMPT = """\
You are the Eligibility Agent for an appointment scheduling system.
Your job is to determine if a booking or cancellation request is eligible.

You have access to the following MCP (Model Context Protocol) tools:

1. check_slot_availability(start_time, end_time)
   - Checks if a time slot is available in the calendar
   - Returns: {is_available: bool, conflicting_events: [...]}

2. find_event_by_booking_code(booking_code)
   - Finds a calendar event by its 4-digit booking code
   - Returns: {found: bool, event: {...}}

─── BOOKING ELIGIBILITY RULES ─────────────────────────────────────────
1. Use check_slot_availability to verify the time slot is free.
2. Respect standard Working Hours: 9 AM - 6 PM IST.
3. Respect Lunch Break: 1:00 PM - 1:30 PM IST (No bookings allowed).
4. Respect National Holidays (data will be provided in the request).

─── CANCELLATION ELIGIBILITY RULES ────────────────────────────────────
1. Use find_event_by_booking_code to verify the booking exists.
2. Check if the booking is in the past (cannot cancel past appointments).
3. Cancellations are only allowed if the appointment has not started yet.

─── BOOKING CODE FORMAT ───────────────────────────────────────────────
Booking codes are always 4-digit numbers (e.g., 1234, 5678).

─── RESPONSE FORMAT ───────────────────────────────────────────────────
Reply with valid JSON only:

{
  "eligible": true | false,
  "reason": "<explanation for user>",
  "mcp_tools_used": ["tool1", "tool2", ...],
  "details": {
    "conflict_found": true | false,
    "conflict_description": "<description if applicable>",
    "knowledge_base_applied": true | false
  }
}

Keep the reason concise and user-friendly.
"""


class EligibilityAgent:
    """Eligibility Agent using Gemini LLM with MCP protocol and RAG."""

    def __init__(self):
        self.mcp_server = get_mcp_server()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._lock = threading.Lock()
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the Gemini model once."""
        creds = get_gemini_eligibility_credentials()
        genai.configure(api_key=creds["api_key"])
        self.model = genai.GenerativeModel(creds["model"])
        logger.info(f"Eligibility Agent initialized with model: {creds['model']}")

    def _call_mcp_tool(self, tool_name: str, parameters: dict) -> dict:
        """Execute an MCP tool with thread-safety."""
        try:
            async def _run():
                return await self.mcp_server.execute_tool(tool_name, parameters)
            
            # Use a lock to prevent concurrent access to non-thread-safe Google API clients
            with self._lock:
                logger.info(f"Calling MCP tool: {tool_name} with params: {parameters}")
                future = self._executor.submit(asyncio.run, _run())
                result = future.result(timeout=20)
                
                # Log outcome for diagnostics
                if result.get("success"):
                    res_obj = result.get("result", {})
                    if tool_name == "find_event_by_booking_code":
                        logger.info(f"Tool {tool_name} found event: {res_obj.get('found')}")
                else:
                    logger.error(f"Tool {tool_name} failed: {result.get('error')}")
                    
                return result
        except Exception as e:
            logger.error(f"MCP tool {tool_name} execution failed: {e}")
            return {"success": False, "error": str(e)}


    def _call_gemini(self, prompt: str, use_fallback: bool = False) -> str:
        """Call Gemini with the given prompt."""
        if use_fallback:
            creds = get_gemini_eligibility_credentials(use_fallback=True)
            genai.configure(api_key=creds["api_key"])
            model = genai.GenerativeModel(creds["model"])
        else:
            model = self.model

        try:
            response = model.generate_content(
                [ELIGIBILITY_SYSTEM_PROMPT, prompt],
                generation_config={"temperature": 0.2, "max_output_tokens": 2048},
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            raise

    def _parse_eligibility_response(self, raw: str) -> dict:
        """Parse the JSON response from Gemini."""
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse eligibility response: {e}\nRaw: {raw}")
            return {
                "eligible": False,
                "reason": "Unable to determine eligibility due to a system error.",
                "details": {"error": "parse_failed"},
            }

    def check_booking_eligibility(
        self,
        topic: str,
        time_slot: str,
    ) -> EligibilityResult:
        """Check if a booking request is eligible using MCP tools and RAG.
        
        Args:
            topic: The appointment topic.
            time_slot: The requested time slot (natural language or ISO format).
            
        Returns:
            EligibilityResult with status and details.
        """
        try:
            # Parse time slot
            start_time, end_time = self._parse_time_slot(time_slot)
            
            # Call MCP tool: check_slot_availability
            # Convert to IST for calendar query since events are stored in IST
            from datetime import timezone
            ist = timezone(timedelta(hours=5, minutes=30))
            start_time_ist = start_time.astimezone(ist)
            end_time_ist = end_time.astimezone(ist)
            mcp_result = self._call_mcp_tool("check_slot_availability", {
                "start_time": start_time_ist.isoformat(),
                "end_time": end_time_ist.isoformat(),
            })
            
            if mcp_result.get("success"):
                availability_data = mcp_result.get("result", {})
                is_available = availability_data.get("is_available", True)
                conflicts_data = availability_data.get("conflicting_events", [])
            else:
                logger.error(f"MCP tool failed: {mcp_result.get('error')}")
                is_available = True  # Assume available if tool fails
                conflicts_data = []
            
            # Check if it's a holiday via CSV lookup
            holiday_found = is_holiday(start_time)
            holiday_msg = f"NATIONAL HOLIDAY: {start_time.strftime('%A, %d %B %Y')} IS A HOLIDAY" if holiday_found else "Not a holiday"
            
            # Log for debugging
            logger.info(f"Slot check: {start_time.isoformat()} to {end_time.isoformat()}")
            logger.info(f"Calendar available: {is_available}, Conflicts: {len(conflicts_data)}")
            if conflicts_data:
                for c in conflicts_data:
                    logger.info(f"  Conflict: {c}")
            
            # Use Gemini to evaluate knowledge base rules (holidays, lunch break, etc.)
            prompt = f"""\
Check booking eligibility:

TOPIC: {topic}
REQUESTED TIME SLOT: {time_slot}
PARSED START TIME: {start_time.isoformat()}
PARSED END TIME: {end_time.isoformat()}

MCP TOOL RESULTS:
- Slot available in calendar: {is_available}
- Conflicting events: {len(conflicts_data)}

EVALUATION CONTEXT:
- Working hours (9 AM - 6 PM IST)
- Lunch break restrictions (1 PM - 1:30 PM IST)
- Holiday status: {holiday_msg}

Respond with valid JSON:
{{
  "eligible": true | false,
  "reason": "<explanation for user, keep it brief>"
}}
"""
            
            try:
                raw_response = self._call_gemini(prompt)
                result = self._parse_eligibility_response(raw_response)
            except Exception as e:
                logger.warning(f"Gemini evaluation failed ({e}), using fallback logic...")
                # Fallback to deterministic checks
                hour = start_time.hour
                minute = start_time.minute
                time_in_minutes = hour * 60 + minute
                
                # Check if it's a holiday
                if is_holiday(start_time):
                    result = {
                        "eligible": False,
                        "reason": f"Sorry, {start_time.strftime('%A, %d %B %Y')} is a national holiday. Please choose a different date.",
                    }
                # Check working hours (9 AM - 6 PM)
                elif hour < 9 or hour >= 18:
                    result = {
                        "eligible": False,
                        "reason": f"Sorry, {time_slot} is outside our working hours of 9 AM - 6 PM. Would you like to book between 9 AM - 6 PM instead?",
                    }
                # Check lunch break (1:00 PM - 1:30 PM = 13:00 - 13:30)
                elif 13 * 60 <= time_in_minutes < 13 * 60 + 30:
                    result = {
                        "eligible": False,
                        "reason": "Sorry, 1:00 PM - 1:30 PM is lunch break. Please choose a different time.",
                    }
                elif not is_available:
                    result = {
                        "eligible": False,
                        "reason": "Sorry, this slot is not available at that time. Please choose a different time.",
                    }
                else:
                    result = {
                        "eligible": True,
                        "reason": "The requested time slot is available.",
                    }

            status = EligibilityStatus.ELIGIBLE if result.get("eligible") else EligibilityStatus.NOT_ELIGIBLE
            
            # Convert conflicts data to CalendarEvent objects
            conflicts = [
                CalendarEvent(
                    id=e.get("id", ""),
                    summary=e.get("summary", ""),
                    start=datetime.fromisoformat(e.get("start", "").replace("Z", "+00:00")),
                    end=datetime.fromisoformat(e.get("end", "").replace("Z", "+00:00")),
                )
                for e in conflicts_data
            ]
            
            return EligibilityResult(
                status=status,
                message=result.get("reason", "Eligibility check completed."),
                requested_slot=start_time.isoformat(),  # Return ISO format for execution
                topic=topic,
                conflicting_events=conflicts,
                knowledge_base_context=None,
            )
            
        except Exception as e:
            logger.exception("Error in booking eligibility check")
            return EligibilityResult(
                status=EligibilityStatus.ERROR,
                message=f"Error checking eligibility: {str(e)}",
                requested_slot=time_slot,
                topic=topic,
            )

    def check_cancellation_eligibility(
        self,
        booking_code: str,
    ) -> EligibilityResult:
        """Check if a cancellation request is eligible using MCP tools and RAG.
        
        Args:
            booking_code: The 4-digit booking code.
            
        Returns:
            EligibilityResult with status and details.
        """
        try:
            # Validate booking code format (4 digits)
            if not re.match(r"^\d{4}$", booking_code):
                return EligibilityResult(
                    status=EligibilityStatus.NOT_ELIGIBLE,
                    message="Invalid booking code. Booking codes are 4-digit numbers (e.g., 1234).",
                    booking_code=booking_code,
                )

            # Call MCP tool: find_event_by_booking_code
            mcp_result = self._call_mcp_tool("find_event_by_booking_code", {
                "booking_code": booking_code,
            })
            
            event_data = None
            event_found = False
            
            if mcp_result.get("success"):
                result_data = mcp_result.get("result", {})
                event_found = result_data.get("found", False)
                event_data = result_data.get("event")
            else:
                logger.error(f"MCP tool failed: {mcp_result.get('error')}")
            
            if not event_found or not event_data:
                return EligibilityResult(
                    status=EligibilityStatus.NOT_ELIGIBLE,
                    message=f"There is no event with {booking_code}. Please check the code and try again.",
                    booking_code=booking_code,
                )

            # Check if appointment is in the past
            from datetime import timezone
            now = datetime.now(timezone.utc)
            event_start = datetime.fromisoformat(event_data.get("start", "").replace("Z", "+00:00"))
            is_past = event_start < now
            
            
            # Build prompt for Gemini with MCP results
            prompt = f"""\
Check cancellation eligibility:

BOOKING CODE: {booking_code}
MCP TOOL RESULTS:
- find_event_by_booking_code: {"Found" if event_found else "Not Found"}
- EVENT: {event_data.get("summary", "")}
- EVENT START: {event_data.get("start", "")}
- CURRENT TIME: {now.isoformat()}
- IS PAST EVENT: {is_past}

Determine if this cancellation is eligible. 
Note: Cancellations are allowed if the appointment is in the future.

Respond with valid JSON:
{{
  "eligible": true | false,
  "reason": "<explanation for user, keep it brief>"
}}
"""
            
            # Call Gemini for eligibility decision
            try:
                raw_response = self._call_gemini(prompt)
                result = self._parse_eligibility_response(raw_response)
            except Exception as e:
                logger.warning(f"Primary Gemini call failed ({e}), using fallback logic...")
                result = {
                    "eligible": not is_past,
                    "reason": "Cannot cancel past appointments." if is_past else "Cancellation is allowed.",
                    "mcp_tools_used": ["find_event_by_booking_code"],
                    "details": {"is_past": is_past},
                }

            status = EligibilityStatus.ELIGIBLE if result.get("eligible") else EligibilityStatus.NOT_ELIGIBLE
            
            # Convert event data to CalendarEvent
            event = CalendarEvent(
                id=event_data.get("id", ""),
                summary=event_data.get("summary", ""),
                start=event_start,
                end=datetime.fromisoformat(event_data.get("end", "").replace("Z", "+00:00")),
                description=event_data.get("description"),
            )
            
            return EligibilityResult(
                status=status,
                message=result.get("reason", "Eligibility check completed."),
                booking_code=booking_code,
                conflicting_events=[event],
            )
            
        except Exception as e:
            logger.exception("Error in cancellation eligibility check")
            return EligibilityResult(
                status=EligibilityStatus.ERROR,
                message=f"Error checking cancellation eligibility: {str(e)}",
                booking_code=booking_code,
            )

    def _parse_time_slot(self, time_slot: str) -> Tuple[datetime, datetime]:
        """Parse a time slot string into start and end datetimes.
        
        Args:
            time_slot: Time slot string (e.g., "tomorrow at 2:00 PM", "2025-04-15T14:00:00").
            
        Returns:
            Tuple of (start_time, end_time).
        """
        from datetime import time, timezone, timedelta as td
        
        # Use IST (UTC+5:30) for date calculations
        ist = timezone(td(hours=5, minutes=30))
        now = datetime.now(ist)
        
        # Try ISO format first
        try:
            start = datetime.fromisoformat(time_slot.replace("Z", "+00:00"))
            end = start + timedelta(hours=1)
            return start, end
        except ValueError:
            pass
        
        import re
        time_slot_lower = time_slot.lower().strip()
        
        logger.info(f"Parsing time slot: '{time_slot}'")
        
        # ── STEP 1: Identify and extract the DATE portion ──
        date = None
        remaining_for_time = time_slot_lower  # text after removing date portion
        
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        current_year = now.year
        
        # Pattern: day + month ("23rd April", "24 April", "23 of april")
        date_pattern1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)', time_slot_lower)
        # Pattern: month + day ("April 23", "April 23rd")
        date_pattern2 = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?', time_slot_lower)
        # Pattern: numeric date DD/MM or DD-MM
        date_pattern3 = re.search(r'(\d{1,2})[/-](\d{1,2})', time_slot_lower)
        
        if date_pattern1:
            day = int(date_pattern1.group(1))
            month = month_names[date_pattern1.group(2)]
            try:
                date = datetime(current_year, month, day).date()
                if date < now.date():
                    date = datetime(current_year + 1, month, day).date()
                logger.info(f"Matched date pattern (day month): {date}")
                # Remove the date portion from the string so it doesn't interfere with time parsing
                remaining_for_time = time_slot_lower[:date_pattern1.start()] + time_slot_lower[date_pattern1.end():]
            except ValueError:
                pass
        elif date_pattern2:
            month = month_names[date_pattern2.group(1)]
            day = int(date_pattern2.group(2))
            try:
                date = datetime(current_year, month, day).date()
                if date < now.date():
                    date = datetime(current_year + 1, month, day).date()
                logger.info(f"Matched date pattern (month day): {date}")
                remaining_for_time = time_slot_lower[:date_pattern2.start()] + time_slot_lower[date_pattern2.end():]
            except ValueError:
                pass
        elif date_pattern3:
            day = int(date_pattern3.group(1))
            month = int(date_pattern3.group(2))
            try:
                date = datetime(current_year, month, day).date()
                if date < now.date():
                    date = datetime(current_year + 1, month, day).date()
                logger.info(f"Matched date pattern (numeric): {date}")
                remaining_for_time = time_slot_lower[:date_pattern3.start()] + time_slot_lower[date_pattern3.end():]
            except ValueError:
                pass
        
        # Day-of-week ("Monday", "next Wednesday", "this Friday")
        if date is None:
            days_of_week = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            for day_name, day_number in days_of_week.items():
                if day_name in time_slot_lower:
                    today = now.date()
                    current_weekday = today.weekday()
                    days_ahead = day_number - current_weekday
                    if days_ahead <= 0 or "next" in time_slot_lower:
                        days_ahead += 7
                    date = today + timedelta(days=days_ahead)
                    logger.info(f"Matched day of week ({day_name}): {date}")
                    # Remove the day name from remaining text
                    remaining_for_time = re.sub(r'(next|this|upcoming|coming)?\s*' + day_name, '', time_slot_lower).strip()
                    break
        
        # Relative dates
        if date is None:
            if "day after tomorrow" in time_slot_lower:
                date = (now + timedelta(days=2)).date()
                remaining_for_time = time_slot_lower.replace('day after tomorrow', '').strip()
                logger.info(f"Matched 'day after tomorrow': {date}")
            elif "tomorrow" in time_slot_lower:
                date = (now + timedelta(days=1)).date()
                remaining_for_time = time_slot_lower.replace('tomorrow', '').strip()
                logger.info(f"Matched 'tomorrow': {date}")
            elif "today" in time_slot_lower:
                date = now.date()
                remaining_for_time = time_slot_lower.replace('today', '').strip()
                logger.info(f"Matched 'today': {date}")
            else:
                logger.warning(f"No date pattern matched for: '{time_slot}'")
                raise ValueError(f"Could not determine date from '{time_slot}'. Please provide a date (e.g., tomorrow, next Monday, 23rd April).")
        
        # ── STEP 2: Parse TIME from the remaining text (date portion removed) ──
        # Normalize AM/PM variants
        remaining_for_time = re.sub(r'p\.?m\.?', 'pm', remaining_for_time)
        remaining_for_time = re.sub(r'a\.?m\.?', 'am', remaining_for_time)
        remaining_for_time = remaining_for_time.replace('afternoon', 'pm').replace('evening', 'pm').replace('morning', 'am')
        remaining_for_time = remaining_for_time.strip(' ,;-@at')
        
        logger.info(f"Remaining text for time parsing: '{remaining_for_time}'")
        
        # Match time with AM/PM (e.g., "3:00 pm", "3.00 pm", "3 pm")
        time_match = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)', remaining_for_time)
        if not time_match:
            # Try 24-hour format (e.g., "15:00", "15.00")
            time_match = re.search(r'(\d{1,2})[:.](\d{2})', remaining_for_time)
        
        hour = 10  # Default fallback
        minute = 0
        
        if time_match:
            hour = int(time_match.group(1))
            if time_match.group(2):
                minute = int(time_match.group(2))
            ampm = time_match.group(3) if time_match.lastindex >= 3 else None
            if ampm and ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm and ampm == 'am' and hour == 12:
                hour = 0
        
        logger.info(f"Parsed time: hour={hour}, minute={minute}")
        
        # ── STEP 3: Combine date + time ──
        start = datetime.combine(date, time(hour, minute))
        start = start.replace(tzinfo=ist)
        end = start + timedelta(hours=1)
        
        logger.info(f"Final parsed: {start.isoformat()}")
        return start, end

    def _format_conflicts(self, conflicts: list) -> str:
        """Format conflicting events for the prompt."""
        if not conflicts:
            return "None"
        return "\n".join([
            f"- {e.summary} ({e.start.strftime('%Y-%m-%d %H:%M')} to {e.end.strftime('%H:%M')})"
            for e in conflicts
        ])


# Singleton instance
_eligibility_agent: Optional[EligibilityAgent] = None


def get_eligibility_agent() -> EligibilityAgent:
    """Get the Eligibility Agent singleton."""
    global _eligibility_agent
    if _eligibility_agent is None:
        _eligibility_agent = EligibilityAgent()
    return _eligibility_agent


# Convenience functions for direct use
def check_booking_eligibility(topic: str, time_slot: str) -> EligibilityResult:
    """Check booking eligibility using the Eligibility Agent."""
    return get_eligibility_agent().check_booking_eligibility(topic, time_slot)


def check_cancellation_eligibility(booking_code: str) -> EligibilityResult:
    """Check cancellation eligibility using the Eligibility Agent."""
    return get_eligibility_agent().check_cancellation_eligibility(booking_code)
