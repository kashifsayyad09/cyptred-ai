"""Shared pytest fixtures for AI Exam Guardian tests."""

import pytest


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return "http://localhost:8000"


# Phase 2+: database fixtures, auth fixtures, session fixtures (require FastAPI + MySQL)
# Phase 4+: MCP client fixtures, rules engine fixtures
# Phase 7+: AI gateway mock fixtures
