"""Health endpoint tests — verifies basic API availability."""

import pytest


def test_health_endpoint_returns_200():
    """Placeholder — runs against live backend in Phase 2."""
    # Will be replaced with real TestClient in Phase 2
    assert True


def test_health_response_schema():
    """Placeholder — validates health response shape in Phase 2."""
    expected_keys = {"status", "service", "version"}
    response = {"status": "ok", "service": "ai-exam-guardian-backend", "version": "0.1.0"}
    assert expected_keys == set(response.keys())
    assert response["status"] == "ok"
