"""
Prometheus metrics middleware.

Records per-request metrics:
  - Request count (method, path, status_code)
  - Request latency (method, path)
  - In-progress gauge (method, path)

Path normalisation: strips path parameters (UUIDs) so cardinality stays low.
E.g. /api/v1/sessions/550e8400-e29b-... → /api/v1/sessions/{id}
"""

from __future__ import annotations

import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_LATENCY,
    HTTP_REQUESTS_IN_PROGRESS,
)

# Patterns to normalise path parameters
_UUID_RE  = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_INT_RE   = re.compile(r"/\d+")


def _normalise_path(path: str) -> str:
    """Replace path parameters with placeholders to reduce cardinality."""
    path = _UUID_RE.sub("{id}", path)
    path = _INT_RE.sub("/{id}", path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records Prometheus HTTP metrics for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        path   = _normalise_path(request.url.path)

        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, path=path).inc()
        started = time.perf_counter()

        try:
            response: Response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            latency = time.perf_counter() - started
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, path=path).dec()
            HTTP_REQUEST_LATENCY.labels(method=method, path=path).observe(latency)
            HTTP_REQUESTS_TOTAL.labels(
                method=method, path=path, status_code=status_code
            ).inc()

        return response
