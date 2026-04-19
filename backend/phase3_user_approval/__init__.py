"""Phase 3 — User Approval Module.

Manages user approval state for booking and cancellation requests
before they proceed to Phase 4 (Execution).
"""

from .models import (
    ApprovalAction,
    ApprovalStatus,
    ApprovalState,
    ApprovalRequest,
    ApprovalConfirmation,
    ApprovalResponse,
    ApprovalSummary,
)
from .approval_manager import (
    ApprovalManager,
    get_approval_manager,
    create_approval,
    process_confirmation,
    get_pending_approval,
    clear_approval,
)
from .config import get_approval_settings

__all__ = [
    # Enums
    "ApprovalAction",
    "ApprovalStatus",
    # Models
    "ApprovalState",
    "ApprovalRequest",
    "ApprovalConfirmation",
    "ApprovalResponse",
    "ApprovalSummary",
    # Manager
    "ApprovalManager",
    "get_approval_manager",
    # Convenience functions
    "create_approval",
    "process_confirmation",
    "get_pending_approval",
    "clear_approval",
    # Config
    "get_approval_settings",
]
