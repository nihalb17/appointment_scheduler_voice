"""MCP (Model Context Protocol) Server for Calendar tools.

Exposes calendar operations as MCP tools that can be called by the Eligibility Agent.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from .calendar_mcp import get_calendar_mcp
from .models import CalendarEvent

logger = logging.getLogger(__name__)


class MCPTool:
    """Represents an MCP tool."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to MCP tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool handler."""
        try:
            result = await self.handler(**kwargs) if hasattr(self.handler, '__await__') else self.handler(**kwargs)
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class CalendarMCPServer:
    """MCP Server exposing calendar tools."""
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.calendar = get_calendar_mcp()
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all calendar tools."""
        # Tool: read_calendar
        self.tools["read_calendar"] = MCPTool(
            name="read_calendar",
            description="Read events from the calendar within a time range",
            parameters={
                "type": "object",
                "properties": {
                    "time_min": {
                        "type": "string",
                        "description": "Start time in ISO format (e.g., 2025-04-15T10:00:00)",
                    },
                    "time_max": {
                        "type": "string",
                        "description": "End time in ISO format (optional)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return",
                        "default": 100,
                    },
                },
                "required": ["time_min"],
            },
            handler=self._handle_read_calendar,
        )
        
        # Tool: check_slot_availability
        self.tools["check_slot_availability"] = MCPTool(
            name="check_slot_availability",
            description="Check if a specific time slot is available",
            parameters={
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO format",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO format",
                    },
                },
                "required": ["start_time", "end_time"],
            },
            handler=self._handle_check_slot_availability,
        )
        
        # Tool: find_event_by_booking_code
        self.tools["find_event_by_booking_code"] = MCPTool(
            name="find_event_by_booking_code",
            description="Find a calendar event by its booking code",
            parameters={
                "type": "object",
                "properties": {
                    "booking_code": {
                        "type": "string",
                        "description": "The 4-digit booking code (e.g., 1234)",
                    },
                },
                "required": ["booking_code"],
            },
            handler=self._handle_find_event_by_booking_code,
        )
        
        logger.info(f"MCP Server registered {len(self.tools)} tools")
    
    def _handle_read_calendar(
        self,
        time_min: str,
        time_max: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Handle read_calendar tool."""
        time_min_dt = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
        time_max_dt = None
        if time_max:
            time_max_dt = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
        
        events = self.calendar.read_calendar(time_min_dt, time_max_dt, max_results)
        
        return {
            "events": [
                {
                    "id": e.id,
                    "summary": e.summary,
                    "start": e.start.isoformat(),
                    "end": e.end.isoformat(),
                    "description": e.description,
                }
                for e in events
            ],
            "count": len(events),
        }
    
    def _handle_check_slot_availability(
        self,
        start_time: str,
        end_time: str,
    ) -> Dict[str, Any]:
        """Handle check_slot_availability tool."""
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        
        is_available, conflicts = self.calendar.check_slot_availability(start_dt, end_dt)
        
        return {
            "is_available": is_available,
            "conflicting_events": [
                {
                    "id": e.id,
                    "summary": e.summary,
                    "start": e.start.isoformat(),
                    "end": e.end.isoformat(),
                }
                for e in conflicts
            ],
            "conflict_count": len(conflicts),
        }
    
    def _handle_find_event_by_booking_code(
        self,
        booking_code: str,
    ) -> Dict[str, Any]:
        """Handle find_event_by_booking_code tool."""
        event = self.calendar.find_event_by_booking_code(booking_code)
        
        if event:
            return {
                "found": True,
                "event": {
                    "id": event.id,
                    "summary": event.summary,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "description": event.description,
                },
            }
        else:
            return {
                "found": False,
                "event": None,
            }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all tool schemas."""
        return [tool.to_schema() for tool in self.tools.values()]
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self.tools.get(name)
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' not found",
            }
        
        return await tool.execute(**parameters)


# Singleton instance
_mcp_server: Optional[CalendarMCPServer] = None


def get_mcp_server() -> CalendarMCPServer:
    """Get or create the MCP Server singleton."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = CalendarMCPServer()
    return _mcp_server
