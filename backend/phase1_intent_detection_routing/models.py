from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ---- Enums ----

class Intent(str, Enum):
    BOOK = "book"
    CANCEL = "cancel"
    OUT_OF_SCOPE = "out_of_scope"
    # Confirmation intents for Phase 4 execution
    BOOK_CONFIRMED = "book_confirmed"
    BOOK_REJECTED = "book_rejected"
    CANCEL_CONFIRMED = "cancel_confirmed"
    CANCEL_REJECTED = "cancel_rejected"


class AppointmentTopic(str, Enum):
    KYC_ONBOARDING = "KYC/Onboarding"
    SIP_MANDATES = "SIP/Mandates"
    STATEMENTS_TAX_DOCS = "Statements/Tax Docs"
    WITHDRAWALS_TIMELINES = "Withdrawals & Timelines"
    ACCOUNT_CHANGES_NOMINEE = "Account Changes/Nominee"


# ---- Request / Response ----

class ChatRequest(BaseModel):
    """Incoming user message."""
    session_id: str
    message: str


class IntentResult(BaseModel):
    """Structured output from the orchestrator after intent classification."""
    intent: Intent
    reply: str
    topic: Optional[AppointmentTopic] = None
    time_slot: Optional[str] = None
    booking_code: Optional[str] = None
    awaiting_eligibility_check: Optional[bool] = False
    eligibility_status: Optional[str] = None  # "pending", "eligible", "not_eligible", None


class ChatResponse(BaseModel):
    """Response returned to the caller."""
    session_id: str
    intent: Intent
    reply: str
    topic: Optional[AppointmentTopic] = None
    time_slot: Optional[str] = None
    booking_code: Optional[str] = None
    awaiting_eligibility_check: Optional[bool] = False
    eligibility_status: Optional[str] = None


# ---- Conversation history ----

class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str
