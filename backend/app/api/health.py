"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

health_router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic liveness probe."""
    return HealthResponse(
        status="ok",
        service="ai-exam-guardian-backend",
        version="0.1.0",
    )


@health_router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness probe — will expand to check DB/MCP/RAG in Phase 2."""
    return HealthResponse(
        status="ok",
        service="ai-exam-guardian-backend",
        version="0.1.0",
    )
