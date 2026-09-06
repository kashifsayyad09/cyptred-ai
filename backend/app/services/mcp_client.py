"""MCP client — used by the FastAPI backend to call MCP server tools."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_MCP_BASE = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}"
_TIMEOUT = 15.0


async def call_tool(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Call an MCP tool by name. Returns the result dict on success.
    Raises httpx.HTTPError on network/server failure.
    """
    url = f"{_MCP_BASE}/tools/{tool_name}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"payload": payload})
        resp.raise_for_status()
        data = resp.json()
        logger.info("mcp_tool_called", tool=tool_name, ok=data.get("ok"))
        return data.get("result", {})


async def calculate_risk_for_session(
    session_id: str,
    events: list[dict[str, Any]],
    exam_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper: calculate risk score for a session."""
    return await call_tool("calculate_risk", {
        "session_id": session_id,
        "events": events,
        "exam_rules": exam_rules or {},
    })


async def get_student_timeline(
    session_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convenience wrapper: build evidence timeline for a session."""
    return await call_tool("get_student_timeline", {
        "session_id": session_id,
        "events": events,
    })


async def create_incident_summary(
    session_id: str,
    events: list[dict[str, Any]],
    risk_score: int,
    risk_level: str,
    exam_title: str = "Examination",
    student_id: str = "",
) -> dict[str, Any]:
    """Convenience wrapper: create incident summary for AI explanation."""
    return await call_tool("create_incident_summary", {
        "session_id": session_id,
        "events": events,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "exam_title": exam_title,
        "student_id": student_id,
    })
