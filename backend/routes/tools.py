"""
Tools API Routes
Handles MCP tool execution and management
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(tags=["tools"])


class ToolExecutionRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any] = {}


@router.get("/tools/available")
async def get_available_tools():
    """Get all available MCP tools for debugging/exploration"""
    try:
        from ..mcp.tool_orchestrator import get_tool_orchestrator

        orchestrator = get_tool_orchestrator()
        tools = orchestrator.get_available_tools()
        stats = orchestrator.get_execution_stats()

        return {
            "success": True,
            "tools": tools,
            "execution_stats": stats,
            "total_tools": len(tools)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tools": {},
            "execution_stats": {},
            "total_tools": 0
        }


@router.post("/tools/execute")
async def execute_tool_directly(request: ToolExecutionRequest):
    """Execute a specific MCP tool directly (for testing/debugging)"""
    try:
        from ..mcp.tool_orchestrator import get_tool_orchestrator

        orchestrator = get_tool_orchestrator()
        result = orchestrator.execute_tool(request.tool_name, request.params)

        return {
            "success": result.success,
            "tool_name": result.tool_name,
            "result": result.result,
            "execution_time_ms": result.execution_time_ms,
            "error": result.error
        }
    except Exception as e:
        return {
            "success": False,
            "tool_name": request.tool_name,
            "result": {},
            "execution_time_ms": 0,
            "error": str(e)
        }
