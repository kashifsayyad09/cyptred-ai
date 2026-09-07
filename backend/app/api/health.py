"""
Health check endpoints.

GET /health  — liveness probe (always responds if the process is alive)
GET /ready   — readiness probe (checks DB, MCP, RAG connectivity)
"""

from __future__ import annotations

import asyncio
import time

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger(__name__)
health_router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessProbe(BaseModel):
    status: str                    # "ready" | "degraded" | "not_ready"
    service: str
    version: str
    checks: dict[str, str]         # component → "ok" | "error: <reason>"
    latency_ms: float


async def _check_component(name: str, url: str, timeout: float = 3.0) -> tuple[str, str]:
    """
    Attempt an HTTP GET to `url`.  Returns (name, "ok") on success or
    (name, "error: <reason>") on failure.  Never raises.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
            if r.status_code < 500:
                return name, "ok"
            return name, f"error: HTTP {r.status_code}"
    except httpx.TimeoutException:
        return name, "error: timeout"
    except Exception as exc:  # noqa: BLE001
        return name, f"error: {exc!r}"


async def _check_database() -> tuple[str, str]:
    """
    Check DB connectivity by importing the engine and running a trivial query.
    Wrapped in try/except so a missing DB never kills the process.
    """
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return "database", "ok"
    except Exception as exc:  # noqa: BLE001
        return "database", f"error: {exc!r}"


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — responds as long as the process is running."""
    return HealthResponse(
        status="ok",
        service="ai-exam-guardian-backend",
        version="0.1.0",
    )


@health_router.get("/ready", response_model=ReadinessProbe)
async def readiness_check() -> ReadinessProbe:
    """
    Readiness probe — checks DB, MCP, and RAG reachability.

    Returns HTTP 200 with status="ready" when all checks pass.
    Returns HTTP 200 with status="degraded" when non-critical components fail.
    Still reports all individual check results for observability.
    """
    start = time.monotonic()

    mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/health"
    rag_url = f"http://{settings.RAG_HOST}:{settings.RAG_PORT}/health"

    # Run all checks concurrently
    results = await asyncio.gather(
        _check_database(),
        _check_component("mcp", mcp_url),
        _check_component("rag", rag_url),
    )

    checks = dict(results)
    latency_ms = round((time.monotonic() - start) * 1000, 2)

    all_ok = all(v == "ok" for v in checks.values())
    status = "ready" if all_ok else "degraded"

    logger.info("readiness_check", status=status, checks=checks, latency_ms=latency_ms)

    return ReadinessProbe(
        status=status,
        service="ai-exam-guardian-backend",
        version="0.1.0",
        checks=checks,
        latency_ms=latency_ms,
    )
