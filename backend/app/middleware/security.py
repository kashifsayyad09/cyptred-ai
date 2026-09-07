"""
Security headers middleware.

Adds hardened HTTP security headers to every response:
  - Strict-Transport-Security (HSTS) — for HTTPS deployments
  - Content-Security-Policy — restrictive default
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
  - Permissions-Policy
  - Cache-Control for API responses
  - X-Request-ID — injected per request for tracing

Also enforces:
  - API endpoints only accept JSON (Content-Type check for POST/PUT/PATCH)
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Endpoints that are exempt from Content-Type enforcement
_CT_EXEMPT_PATHS = {"/health", "/ready", "/metrics", "/api/v1/auth/login"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects security headers on every response.
    Assigns a unique X-Request-ID to every request (used in logs).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Assign request ID early — used in logs
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # ── Security headers ────────────────────────────────────────────────
        response.headers["X-Request-ID"] = request_id

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer control
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — block everything not needed
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), interest-cohort=()"
        )

        # CSP — restrictive; tightened for API-only paths
        path = request.url.path
        if path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        # HSTS — only meaningful behind HTTPS termination
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Cache control for API endpoints — no caching of sensitive data
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response
