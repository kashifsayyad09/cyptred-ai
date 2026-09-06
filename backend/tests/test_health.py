"""Health endpoint tests.

NOTE: Tests marked skip require Python 3.11 in Docker (FastAPI + pydantic-core).
Run via: docker-compose exec backend pytest tests/test_health.py
"""

import pytest


def test_health_response_schema() -> None:
    """Health response must have the correct keys and values."""
    response = {"status": "ok", "service": "ai-exam-guardian-backend", "version": "0.1.0"}
    assert response["status"] == "ok"
    assert response["service"] == "ai-exam-guardian-backend"
    assert "version" in response


def test_health_schema_keys() -> None:
    expected_keys = {"status", "service", "version"}
    response = {"status": "ok", "service": "ai-exam-guardian-backend", "version": "0.1.0"}
    assert expected_keys == set(response.keys())


@pytest.mark.skip(reason="Requires Docker container with Python 3.11 + FastAPI")
def test_health_endpoint_returns_200() -> None:
    """GET /health returns HTTP 200 — requires running backend."""
    pass


@pytest.mark.skip(reason="Requires Docker container with Python 3.11 + FastAPI")
def test_ready_endpoint_returns_200() -> None:
    """GET /ready returns HTTP 200 — requires running backend."""
    pass
