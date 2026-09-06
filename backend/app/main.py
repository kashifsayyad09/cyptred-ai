"""AI Exam Guardian — FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.router import api_router
from app.api.health import health_router

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
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Routers
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
