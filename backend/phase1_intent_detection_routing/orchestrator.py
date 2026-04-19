import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from groq import Groq

from .config import get_groq_credentials
from .models import Intent, IntentResult, Message
from .prompts import SYSTEM_PROMPT

# Add parent directory to path for importing phase2
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from phase2_eligibility_check.eligibility_agent import check_booking_eligibility, check_cancellation_eligibility
from phase2_eligibility_check.models import EligibilityStatus

logger = logging.getLogger(__name__)

# In-memory session store: session_id -> list of message dicts
_sessions: Dict[str, List[dict]] = {}


def _get_system_prompt() -> str:
    """Build system prompt with current date context for accurate date calculations."""
    today = datetime.now()
    today_str = today.strftime("%A, %d %B %Y")
    tomorrow_str = (today.replace(day=today.day + 1)).strftime("%A, %d %B %Y")
    
    date_context = f"""\n\n─── CURRENT DATE CONTEXT ─────────────────────────────────────────────\nToday is {today_str} IST.\nTomorrow will be {tomorrow_str} IST.\nAll appointments are scheduled in IST (Indian Standard Time).\nWhen confirming bookings, always show the full date, day, and time with IST.\n"""
    
    return SYSTEM_PROMPT + date_context


def _get_history(session_id: str) -> List[dict]:
    """Return (and lazily initialise) the conversation history for a session."""
    if session_id not in _sessions:
        _sessions[session_id] = [{"role": "system", "content": _get_system_prompt()}]
    return _sessions[session_id]


def _call_groq(messages: List[dict], use_fallback: bool = False) -> str:
    """Send messages to Groq and return the raw assistant content."""
    creds = get_groq_credentials(use_fallback=use_fallback)
    client = Groq(api_key=creds["api_key"])
    response = client.chat.completions.create(
        model=creds["model"],
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _parse_response(raw: str) -> IntentResult:
    """Parse the JSON response from the LLM into an IntentResult."""
    # Strip markdown fences if the model wraps the JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[: cleaned.rfind("```")]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)
    return IntentResult(**data)


# Track sessions that have pending confirmations
_pending_confirmations: Dict[str, dict] = {}

# Store original time_slot in ISO format for execution
_session_time_slots: Dict[str, str] = {}


def _check_eligibility_and_update_result(
    result: IntentResult, user_message: str = "", session_id: str = ""
) -> IntentResult:
    """Check eligibility if booking intent with topic and time_slot present,
    or cancellation intent with booking_code present.
    
    Args:
        result: The IntentResult from LLM parsing.
        user_message: The raw user message for confirmation detection.
        session_id: The session ID for tracking pending confirmations.
        
    Returns:
        Updated IntentResult with eligibility status.
    """
    global _pending_confirmations, _session_time_slots
    
    # Check if user is responding to a pending confirmation
    pending = _pending_confirmations.get(session_id)
    is_confirmation_response = any(word in user_message.lower() for word in ["yes", "yeah", "sure", "ok", "okay", "confirm", "proceed", "go ahead"])
    is_rejection_response = any(word in user_message.lower() for word in ["no", "nope", "cancel", "reject", "don't", "dont"])
    
    # If user is confirming a pending booking
    if pending and pending.get("type") == "book" and is_confirmation_response:
        logger.info(f"User confirmed booking for session {session_id}")
        result.intent = Intent.BOOK_CONFIRMED
        result.reply = "Confirmed. Proceeding with your booking..."
        # Ensure topic is set - use pending data or result from LLM
        if not result.topic:
            result.topic = pending.get("topic")
        # Use the stored ISO format time_slot for execution
        iso_time_slot = _session_time_slots.get(session_id) or pending.get("time_slot")
        if iso_time_slot:
            result.time_slot = iso_time_slot
        result.eligibility_status = "eligible"
        result.awaiting_eligibility_check = False
        logger.info(f"Booking confirmed - Topic: {result.topic}, Time: {result.time_slot}")
        # Clear the pending confirmation
        del _pending_confirmations[session_id]
        return result
    
    # If user is rejecting a pending booking
    if pending and pending.get("type") == "book" and is_rejection_response:
        logger.info(f"User rejected booking for session {session_id}")
        result.intent = "book_rejected"
        result.reply = "Booking cancelled. If you'd like to book a different time, please let me know."
        result.eligibility_status = "rejected"
        result.awaiting_eligibility_check = False
        del _pending_confirmations[session_id]
        return result
    
    # If user is confirming a pending cancellation
    if pending and pending.get("type") == "cancel" and is_confirmation_response:
        logger.info(f"User confirmed cancellation for session {session_id}")
        result.intent = "cancel_confirmed"
        result.reply = "Confirmed. Proceeding with cancellation..."
        result.booking_code = pending.get("booking_code")
        result.eligibility_status = "eligible"
        result.awaiting_eligibility_check = False
        del _pending_confirmations[session_id]
        return result
    
    # If user is rejecting a pending cancellation
    if pending and pending.get("type") == "cancel" and is_rejection_response:
        logger.info(f"User rejected cancellation for session {session_id}")
        result.intent = "cancel_rejected"
        result.reply = "Cancellation cancelled. Your appointment remains scheduled."
        result.eligibility_status = "rejected"
        result.awaiting_eligibility_check = False
        del _pending_confirmations[session_id]
        return result
    
    # Check if this is a booking with both topic and time_slot
    if (result.intent == "book" and 
        result.topic and 
        result.time_slot and
        result.awaiting_eligibility_check):
        
        logger.info(f"Checking eligibility for {result.topic} at {result.time_slot}")
        
        try:
            # Call Phase 2 eligibility check
            eligibility_result = check_booking_eligibility(
                topic=result.topic,
                time_slot=result.time_slot,
            )
            
            # Update result based on eligibility
            if eligibility_result.status == EligibilityStatus.ELIGIBLE:
                result.eligibility_status = "eligible"
                result.awaiting_eligibility_check = False
                # Store the original time_slot in ISO format for execution
                # The eligibility agent returns the parsed datetime in requested_slot
                iso_time_slot = eligibility_result.requested_slot or result.time_slot
                _session_time_slots[session_id] = iso_time_slot
                # Update result.time_slot to ISO format for execution
                result.time_slot = iso_time_slot
                # Store pending confirmation for this session
                _pending_confirmations[session_id] = {
                    "type": "book",
                    "topic": result.topic,
                    "time_slot": iso_time_slot,
                }
                # Update reply to show confirmation prompt (use display format)
                if "shall i proceed" not in result.reply.lower():
                    # Parse the ISO time to create a display format with full date
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(iso_time_slot)
                        display_datetime = dt.strftime("%A, %d %B %Y at %I:%M %p IST")
                    except:
                        display_datetime = iso_time_slot
                    result.reply = f"The slot is available. Shall I proceed with booking a {result.topic.value} appointment for {display_datetime}?"
            else:
                result.eligibility_status = "not_eligible"
                result.awaiting_eligibility_check = False
                # Replace the reply with the eligibility message
                result.reply = eligibility_result.message
                # Clear topic/time_slot so we don't trigger eligibility again
                result.topic = None
                result.time_slot = None
                
        except Exception as e:
            logger.error(f"Eligibility check failed: {e}")
            # If it's a date parsing error, ask the user for a date
            if "Could not determine date" in str(e):
                result.eligibility_status = None
                result.awaiting_eligibility_check = False
                result.reply = "What date would you like to book for? (e.g., tomorrow, next Monday, 23rd April)"
                result.time_slot = None
            else:
                # For other errors, assume eligible and let user confirm
                result.eligibility_status = "eligible"
                result.awaiting_eligibility_check = False
    
    # Check if this is a cancellation with a booking code
    elif (result.intent == "cancel" and result.booking_code):
        
        logger.info(f"Checking cancellation eligibility for booking code {result.booking_code}")
        
        try:
            # Call Phase 2 cancellation eligibility check
            eligibility_result = check_cancellation_eligibility(
                booking_code=result.booking_code,
            )
            
            # Update result based on eligibility
            if eligibility_result.status == EligibilityStatus.ELIGIBLE:
                result.eligibility_status = "eligible"
                result.awaiting_eligibility_check = False
                # Store pending confirmation for this session
                _pending_confirmations[session_id] = {
                    "type": "cancel",
                    "booking_code": result.booking_code,
                }
                # Update reply to show confirmation prompt
                result.reply = f"I found your appointment. Shall I proceed with cancelling booking code {result.booking_code}?"
                logger.info(f"Cancellation eligible for {result.booking_code}, awaiting confirmation")
            else:
                result.eligibility_status = "not_eligible"
                result.awaiting_eligibility_check = False
                # Replace the reply with the eligibility message
                result.reply = eligibility_result.message
                # Clear booking_code so we don't trigger eligibility again
                result.booking_code = None
                logger.info(f"Cancellation not eligible: {eligibility_result.message}")
                
        except Exception as e:
            logger.error(f"Cancellation eligibility check failed: {e}")
            # If eligibility check fails, show error
            result.eligibility_status = "not_eligible"
            result.awaiting_eligibility_check = False
            spoken_code = " ".join(list(str(result.booking_code))) if result.booking_code else ""
            result.reply = f"There is no event with {spoken_code}. Please check the code and try again."
    
    return result


def handle_message(session_id: str, user_message: str) -> IntentResult:
    """Process a single user message through the orchestrator.

    1. Append user message to session history.
    2. Call Groq (with automatic fallback on failure).
    3. Parse structured JSON response.
    4. Check eligibility if booking with topic and time_slot.
    5. Append assistant reply to history for multi-turn context.
    6. Return IntentResult.
    """
    history = _get_history(session_id)
    history.append({"role": "user", "content": user_message})

    # Try primary, fall back to secondary on any error
    raw_response: str = ""
    try:
        raw_response = _call_groq(history, use_fallback=False)
    except Exception as exc:
        logger.warning("Primary Groq call failed (%s), trying fallback…", exc)
        try:
            raw_response = _call_groq(history, use_fallback=True)
        except Exception as fallback_exc:
            logger.error("Fallback Groq call also failed: %s", fallback_exc)
            raise fallback_exc

    # Parse the structured JSON from the LLM
    try:
        result = _parse_response(raw_response)
    except (json.JSONDecodeError, ValueError) as parse_err:
        logger.error("Failed to parse LLM response: %s\nRaw: %s", parse_err, raw_response)
        # Return a safe fallback so the user isn't stuck
        result = IntentResult(
            intent="out_of_scope",
            reply="I'm sorry, I encountered an issue. Could you please rephrase your request?",
        )

    # Check eligibility if needed (Phase 2 integration)
    result = _check_eligibility_and_update_result(result, user_message, session_id)

    # FINAL SAFEGUARD: If we are in book_confirmed/cancel_confirmed, overwrite LLM response
    # to ensure Phase 4 execution is correctly triggered.
    if result.intent == Intent.BOOK_CONFIRMED:
        result.reply = "Confirmed. Proceeding with your booking..."
    elif result.intent == Intent.CANCEL_CONFIRMED:
        result.reply = "Confirmed. Proceeding with your cancellation..."

    # Store assistant reply in history for multi-turn context
    if result.reply:
        history.append({"role": "assistant", "content": json.dumps({"intent": result.intent, "reply": result.reply})})

    return result
