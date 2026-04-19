"""Map orchestrator + execution results to voice replies and call-ended payloads."""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from phase1_intent_detection_routing.models import Intent, IntentResult
from phase4_execution.execution_manager import execute_booking, execute_cancellation
from phase4_execution.models import BookingExecutionRequest, CancellationExecutionRequest
from phase5_confirmation.confirmation_manager import build_confirmation
from phase5_confirmation.models import ConfirmationAction, ConfirmationRequest


def _topic_str(result: IntentResult) -> str:
    if result.topic is None:
        return ""
    return result.topic.value if hasattr(result.topic, "value") else str(result.topic)


def _scheduled_display(iso_str: Optional[str]) -> Optional[str]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except ValueError:
        return iso_str


def resolve_voice_turn(
    session_id: str, result: IntentResult
) -> Tuple[str, bool, Optional[Dict[str, Any]]]:
    """
    Returns (spoken_reply, call_ended, call_ended_payload).
    When call_ended is True, payload is sent after TTS completes.
    """
    if result.intent == Intent.BOOK_CONFIRMED and result.topic and result.time_slot:
        er = execute_booking(
            BookingExecutionRequest(
                session_id=session_id,
                topic=_topic_str(result),
                time_slot=result.time_slot,
            )
        )
        if er.success and er.result:
            conf = build_confirmation(
                ConfirmationRequest(
                    session_id=session_id,
                    action=ConfirmationAction.BOOK,
                    success=True,
                    user_message=er.user_message,
                    booking_code=er.result.booking_code,
                    event_link=er.result.calendar_event.event_link
                    if er.result.calendar_event
                    else None,
                    doc_link=er.result.google_doc.doc_link
                    if er.result.google_doc
                    else None,
                    scheduled_time=er.result.calendar_event.start_time.isoformat()
                    if er.result.calendar_event and er.result.calendar_event.start_time
                    else None,
                )
            )
            st = er.result.calendar_event.start_time if er.result.calendar_event else None
            payload = {
                "action": "book",
                "headline": "CALL ENDED",
                "message": er.user_message,
                "booking_code": er.result.booking_code,
                "scheduled_display": _scheduled_display(st.isoformat() if st else None),
                "banner_text": conf.banner_text,
                "event_link": er.result.calendar_event.event_link
                if er.result.calendar_event
                else None,
            }
            return er.user_message, True, payload
        return er.user_message, False, None

    if result.intent == Intent.CANCEL_CONFIRMED and result.booking_code:
        er = execute_cancellation(
            CancellationExecutionRequest(
                session_id=session_id,
                booking_code=result.booking_code,
            )
        )
        if er.success:
            conf = build_confirmation(
                ConfirmationRequest(
                    session_id=session_id,
                    action=ConfirmationAction.CANCEL,
                    success=True,
                    user_message=er.user_message,
                    booking_code=result.booking_code,
                )
            )
            payload = {
                "action": "cancel",
                "headline": "CALL ENDED",
                "message": er.user_message,
                "booking_code": (er.result.booking_code if er.result else None)
                or result.booking_code,
                "scheduled_display": None,
                "banner_text": conf.banner_text,
            }
            return er.user_message, True, payload
        return er.user_message, False, None

    return result.reply, False, None
