"""Confirmation Manager for Phase 5 — Confirmation.

Receives execution results from Phase 4 (Booking or Cancellation agents) and
builds the final confirmation message to be sent to the user via the Orchestrator.
"""

import logging
from typing import Optional

from .models import (
    ConfirmationAction,
    ConfirmationStatus,
    ConfirmationRequest,
    ConfirmationResponse,
)

logger = logging.getLogger(__name__)


class ConfirmationManager:
    """Builds confirmation messages from Phase 4 execution results.

    Responsibilities:
    1. Receive the execution result from the Booking or Cancellation agent.
    2. Build a user-friendly confirmation message summarising what was done.
    3. Signal the frontend to show a confirmation banner and close the chat input.
    """

    def build_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """Build a confirmation response from an execution result.

        Args:
            request: The confirmation request containing execution details.

        Returns:
            ConfirmationResponse with banner text and close_chat flag.
        """
        logger.info(
            f"ConfirmationManager: Building confirmation for session {request.session_id}, "
            f"action={request.action}, success={request.success}"
        )

        if request.success:
            status = ConfirmationStatus.SUCCESS
            banner_text = self._build_success_banner(request.action)
            close_chat = True
        else:
            status = ConfirmationStatus.FAILED
            banner_text = self._build_failure_banner(request.action)
            close_chat = False

        return ConfirmationResponse(
            session_id=request.session_id,
            action=request.action,
            status=status,
            confirmed=request.success,
            user_message=request.user_message,
            banner_text=banner_text,
            booking_code=request.booking_code,
            event_link=request.event_link,
            doc_link=request.doc_link,
            close_chat=close_chat,
        )

    def _build_success_banner(self, action: ConfirmationAction) -> str:
        """Build a short banner text for successful actions."""
        if action == ConfirmationAction.BOOK:
            return "Appointment confirmed"
        return "Appointment cancelled"

    def _build_failure_banner(self, action: ConfirmationAction) -> str:
        """Build a short banner text for failed actions."""
        if action == ConfirmationAction.BOOK:
            return "Booking failed"
        return "Cancellation failed"


# Singleton instance
_confirmation_manager: Optional[ConfirmationManager] = None


def get_confirmation_manager() -> ConfirmationManager:
    """Get or create the Confirmation Manager singleton."""
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager


# Convenience function
def build_confirmation(request: ConfirmationRequest) -> ConfirmationResponse:
    """Build a confirmation response from execution results."""
    return get_confirmation_manager().build_confirmation(request)
