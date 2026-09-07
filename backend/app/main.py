"""AI Exam Guardian — FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.router import api_router
from app.api.health import health_router
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.metrics import MetricsMiddleware

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    logger.info("ai_exam_guardian_starting", env=settings.APP_ENV, version="0.1.0")
    yield
    logger.info("ai_exam_guardian_stopping")


app = FastAPI(
    title="AI Exam Guardian API",
    description="Privacy-first exam integrity platform backend",
    version="0.1.0",
    lifespan=lifespan,
    # Docs disabled in production — never expose internal API schemas publicly
    docs_url="/docs"  if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# ── Middleware (order matters: outermost = first to process request) ───────────

# Metrics first so it captures all requests including those rejected by CORS
app.add_middleware(MetricsMiddleware)

# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)

# CORS — only allow configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Prometheus metrics endpoint ───────────────────────────────────────────────
# Mounted at /metrics — internal only (Nginx should NOT proxy this publicly)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
