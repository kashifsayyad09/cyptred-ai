"""
AI Exam Guardian — MCP Server

Exposes all 15 MCP tools as HTTP endpoints consumed by the FastAPI backend.
Each endpoint validates the request, calls the tool handler, and returns
a structured JSON response.

All risk scoring is DETERMINISTIC — LLMs do not set numerical scores.
This server continues operating even when AI providers are unavailable.
"""

from __future__ import annotations

import structlog
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from mcp.tools import TOOL_REGISTRY

logger = structlog.get_logger(__name__)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    payload: dict[str, Any] = {}


class ToolResponse(BaseModel):
    tool: str
    result: dict[str, Any]
    ok: bool = True


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    tools_available: list[str]


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Exam Guardian MCP Server",
        description=(
            "Exposes deterministic MCP tools for exam integrity analysis. "
            "Risk scoring is deterministic — LLMs do not influence numerical scores."
        ),
        version="0.4.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # internal service — Nginx restricts externally
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    router = APIRouter()

    # ── Health ────────────────────────────────────────────────────────────────
    @router.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="mcp-server",
            version="0.4.0",
            tools_available=list(TOOL_REGISTRY.keys()),
        )

    # ── Dynamic tool dispatcher ───────────────────────────────────────────────
    @router.post("/tools/{tool_name}", response_model=ToolResponse, tags=["Tools"])
    async def call_tool(tool_name: str, req: ToolRequest) -> ToolResponse:
        handler = TOOL_REGISTRY.get(tool_name)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown tool: {tool_name}. Available: {list(TOOL_REGISTRY)}",
            )
        try:
            result = handler(req.payload)
            logger.info("tool_called", tool=tool_name)
            return ToolResponse(tool=tool_name, result=result)
        except Exception as exc:
            logger.error("tool_error", tool=tool_name, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool execution failed: {exc}",
            ) from exc

    # ── Named shortcuts (keep REST semantics for common tools) ────────────────
    for _name in TOOL_REGISTRY:
        # All tools accessible via POST /tools/{name} above — no duplication needed
        pass

    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import os
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("MCP_PORT", "8001")),
        reload=False,
        log_level="info",
    )
