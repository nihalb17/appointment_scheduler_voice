"""Phase 2 — Eligibility Check

This module handles eligibility verification for booking and cancellation requests
using the Eligibility Agent (Gemini) with MCP protocol and RAG-based knowledge base.
"""

from .eligibility_agent import EligibilityAgent, check_booking_eligibility, check_cancellation_eligibility
from .models import EligibilityResult, EligibilityStatus
from .mcp_server import get_mcp_server, CalendarMCPServer
from .rag_retriever import get_rag_retriever, RAGRetriever, retrieve_context
from .vector_store import get_vector_store, VectorStore

__all__ = [
    "EligibilityAgent",
    "check_booking_eligibility",
    "check_cancellation_eligibility",
    "EligibilityResult",
    "EligibilityStatus",
    "get_mcp_server",
    "CalendarMCPServer",
    "get_rag_retriever",
    "RAGRetriever",
    "retrieve_context",
    "get_vector_store",
    "VectorStore",
]
