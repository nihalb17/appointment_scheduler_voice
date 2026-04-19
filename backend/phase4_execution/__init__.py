"""Phase 4 — Execution Agent.

This module handles the execution of booking and cancellation workflows
after user approval has been granted. It integrates with Google Workspace
via MCP tools (Calendar, Docs, Gmail, Sheets).
"""

from .execution_manager import ExecutionManager, get_execution_manager
from .booking_agent import BookingAgent
from .cancellation_agent import CancellationAgent
from .models import (
    ExecutionAction,
    ExecutionStatus,
    ExecutionResult,
    BookingExecutionRequest,
    CancellationExecutionRequest,
    ExecutionResponse,
)

__all__ = [
    "ExecutionManager",
    "get_execution_manager",
    "BookingAgent",
    "CancellationAgent",
    "ExecutionAction",
    "ExecutionStatus",
    "ExecutionResult",
    "BookingExecutionRequest",
    "CancellationExecutionRequest",
    "ExecutionResponse",
]
