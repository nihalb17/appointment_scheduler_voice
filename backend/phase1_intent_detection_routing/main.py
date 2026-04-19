import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for importing phase2 and phase3
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase1_intent_detection_routing.models import ChatRequest, ChatResponse
from phase1_intent_detection_routing.orchestrator import handle_message

# Import Phase 2 components
from phase2_eligibility_check.models import (
    BookingEligibilityRequest,
    CancellationEligibilityRequest,
    EligibilityCheckResponse,
)
from phase2_eligibility_check.eligibility_agent import (
    check_booking_eligibility,
    check_cancellation_eligibility,
)
from phase2_eligibility_check.internal_dashboard import router as internal_router

# Import Phase 3 components
from phase3_user_approval.models import (
    ApprovalRequest,
    ApprovalConfirmation,
    ApprovalResponse,
)
from phase3_user_approval.approval_manager import (
    create_approval,
    process_confirmation,
    get_pending_approval,
)

# Import Phase 4 components
from phase4_execution.models import (
    BookingExecutionRequest,
    CancellationExecutionRequest,
    ExecutionResponse,
)
from phase4_execution.execution_manager import (
    execute_booking,
    execute_cancellation,
)

# Import Phase 5 components
from phase5_confirmation.models import (
    ConfirmationRequest,
    ConfirmationResponse,
)
from phase5_confirmation.confirmation_manager import (
    build_confirmation,
)

from phase6_voice.ws_handler import handle_voice_websocket


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent Appointment Scheduler",
    description="Phases 1-6: Core pipeline + Voice (streaming STT/TTS)",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include internal dashboard routes
app.include_router(internal_router)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle a single user message and return the orchestrator's response."""
    try:
        result = handle_message(
            session_id=request.session_id,
            user_message=request.message,
        )
        return ChatResponse(
            session_id=request.session_id,
            intent=result.intent,
            reply=result.reply,
            topic=result.topic,
            time_slot=result.time_slot,
            booking_code=result.booking_code,
            awaiting_eligibility_check=result.awaiting_eligibility_check,
            eligibility_status=result.eligibility_status,
        )
    except Exception as exc:
        logger.exception("Error handling chat message")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/eligibility/book", response_model=EligibilityCheckResponse)
async def check_booking_eligibility_endpoint(request: BookingEligibilityRequest):
    """Check if a booking request is eligible.
    
    Phase 2: Eligibility Agent checks calendar availability and knowledge base rules.
    """
    try:
        result = check_booking_eligibility(
            topic=request.topic,
            time_slot=request.time_slot,
        )
        
        return EligibilityCheckResponse(
            session_id=request.session_id,
            status=result.status,
            message=result.message,
            can_proceed=result.status.value == "eligible",
            details={
                "topic": result.topic,
                "requested_slot": result.requested_slot,
                "conflicting_events": [
                    {
                        "id": e.id,
                        "summary": e.summary,
                        "start": e.start.isoformat(),
                        "end": e.end.isoformat(),
                    }
                    for e in result.conflicting_events
                ],
            } if result.conflicting_events else None,
        )
    except Exception as exc:
        logger.exception("Error checking booking eligibility")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/eligibility/cancel", response_model=EligibilityCheckResponse)
async def check_cancellation_eligibility_endpoint(request: CancellationEligibilityRequest):
    """Check if a cancellation request is eligible.
    
    Phase 2: Eligibility Agent verifies booking code and checks cancellation policies.
    """
    try:
        result = check_cancellation_eligibility(
            booking_code=request.booking_code,
        )
        
        return EligibilityCheckResponse(
            session_id=request.session_id,
            status=result.status,
            message=result.message,
            can_proceed=result.status.value == "eligible",
            details={
                "booking_code": result.booking_code,
                "event_found": len(result.conflicting_events) > 0,
                "event_summary": result.conflicting_events[0].summary if result.conflicting_events else None,
            } if result.conflicting_events else None,
        )
    except Exception as exc:
        logger.exception("Error checking cancellation eligibility")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/approval/create", response_model=ApprovalResponse)
async def create_approval_endpoint(request: ApprovalRequest):
    """Create a new approval request after eligibility check passes.
    
    Phase 3: User Approval - Creates a pending approval that awaits user confirmation.
    """
    try:
        result = create_approval(request)
        return result
    except Exception as exc:
        logger.exception("Error creating approval")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/approval/confirm", response_model=ApprovalResponse)
async def confirm_approval_endpoint(request: ApprovalConfirmation):
    """Process user confirmation or rejection.
    
    Phase 3: User Approval - Processes the user's decision to approve or reject.
    """
    try:
        result = process_confirmation(request)
        return result
    except Exception as exc:
        logger.exception("Error processing approval confirmation")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/approval/pending/{session_id}")
async def get_pending_approval_endpoint(session_id: str):
    """Get the pending approval for a session.
    
    Phase 3: User Approval - Check if there's a pending approval awaiting confirmation.
    """
    try:
        approval = get_pending_approval(session_id)
        if approval:
            return {
                "has_pending_approval": True,
                "approval": {
                    "action": approval.action,
                    "status": approval.status,
                    "topic": approval.topic,
                    "time_slot": approval.time_slot,
                    "booking_code": approval.booking_code,
                    "event_summary": approval.event_summary,
                    "created_at": approval.created_at.isoformat(),
                    "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
                },
            }
        return {"has_pending_approval": False}
    except Exception as exc:
        logger.exception("Error getting pending approval")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/execution/book", response_model=ExecutionResponse)
async def execute_booking_endpoint(request: BookingExecutionRequest):
    """Execute a booking after user approval.
    
    Phase 4: Execution - Creates calendar event, Google Doc, sends email, logs to sheets.
    """
    try:
        result = execute_booking(request)
        return result
    except Exception as exc:
        logger.exception("Error executing booking")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/execution/cancel", response_model=ExecutionResponse)
async def execute_cancellation_endpoint(request: CancellationExecutionRequest):
    """Execute a cancellation after user approval.
    
    Phase 4: Execution - Removes calendar event, sends email, logs to sheets.
    """
    try:
        result = execute_cancellation(request)
        return result
    except Exception as exc:
        logger.exception("Error executing cancellation")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/confirmation/build", response_model=ConfirmationResponse)
async def build_confirmation_endpoint(request: ConfirmationRequest):
    """Build a confirmation message after execution completes.
    
    Phase 5: Confirmation - Builds the final confirmation for the user.
    """
    try:
        result = build_confirmation(request)
        return result
    except Exception as exc:
        logger.exception("Error building confirmation")
        raise HTTPException(status_code=500, detail=str(exc))


@app.websocket("/voice/ws")
async def voice_websocket_endpoint(websocket: WebSocket):
    await handle_voice_websocket(websocket)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "phases": [
            "1 — Intent Detection & Routing",
            "2 — Eligibility Check",
            "3 — User Approval",
            "4 — Execution",
            "5 — Confirmation",
            "6 — Voice (Sarvam streaming)",
        ],
        "features": [
            "chat",
            "voice_ws",
            "eligibility_check",
            "approval",
            "execution",
            "confirmation",
            "internal_dashboard",
        ],
    }
