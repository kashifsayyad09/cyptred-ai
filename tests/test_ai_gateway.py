"""
AI Gateway tests — Phase 7 implementation.

Tests the critical failover scenarios:
  - Groq success → Groq used
  - Groq 429     → NVIDIA used
  - Groq timeout → NVIDIA used
  - Both fail    → degraded response
  - Both fail    → deterministic Rules Engine still works

Run:
    python -m pytest tests/test_ai_gateway.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest

# ── Path bootstrap ──────────────────────────────────────────────────────────
_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
_MCP     = os.path.join(os.path.dirname(__file__), "..", "mcp")
for _p in (_BACKEND, _MCP):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("GROQ_API_KEY",    "test-groq-key")
os.environ.setdefault("GROQ_BASE_URL",   "https://api.groq.com/openai/v1")
os.environ.setdefault("GROQ_MODEL",      "llama3-8b-8192")
os.environ.setdefault("GROQ_TIMEOUT_SECONDS", "30")
os.environ.setdefault("GROQ_MAX_RETRIES", "2")
os.environ.setdefault("NVIDIA_API_KEY",  "test-nvidia-key")
os.environ.setdefault("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
os.environ.setdefault("NVIDIA_MODEL",    "meta/llama3-8b-instruct")
os.environ.setdefault("NVIDIA_TIMEOUT_SECONDS", "30")
os.environ.setdefault("NVIDIA_MAX_RETRIES", "2")
os.environ.setdefault("JWT_SECRET_KEY",  "test-jwt-secret")
os.environ.setdefault("APP_SECRET_KEY",  "test-app-secret")

from app.services.ai_gateway.config import GatewayConfig
from app.services.ai_gateway.gateway import AIGateway, ProviderStatus
from app.services.ai_gateway.providers import FallbackReason, ProviderCallResult


def _cfg() -> GatewayConfig:
    return GatewayConfig(
        groq_api_key="test-groq",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama3-8b-8192",
        groq_timeout=5.0,
        groq_max_retries=1,
        nvidia_api_key="test-nvidia",
        nvidia_base_url="https://integrate.api.nvidia.com/v1",
        nvidia_model="meta/llama3-8b-instruct",
        nvidia_timeout=5.0,
        nvidia_max_retries=1,
        health_check_interval=60,
        recovery_threshold=3,
    )


def _ok(provider: str = "groq") -> ProviderCallResult:
    return ProviderCallResult(
        success=True, provider=provider,
        request_id=str(uuid.uuid4()),
        content="Session shows behavioral patterns warranting review.",
        model="llama3-8b-8192", latency_ms=400, http_status=200,
    )


def _fail(provider: str, reason: FallbackReason, status: int | None = None) -> ProviderCallResult:
    return ProviderCallResult(
        success=False, provider=provider,
        request_id=str(uuid.uuid4()),
        latency_ms=50, http_status=status,
        failure_reason=reason, error_detail="test",
    )


def _run(coro):
    """Run a coroutine, creating a new event loop if necessary (Python 3.14+)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


def test_groq_primary_used_on_success():
    """When Groq succeeds, it should be used (not NVIDIA)."""
    from unittest.mock import AsyncMock
    gw = AIGateway(config=_cfg())
    groq_mock  = AsyncMock(return_value=_ok("groq"))
    nvidia_mock = AsyncMock(return_value=_ok("nvidia"))
    gw._groq.complete   = groq_mock
    gw._nvidia.complete = nvidia_mock

    result = _run(gw.complete("explain"))

    assert result.success is True
    assert result.provider == "groq"
    assert result.is_fallback is False
    assert result.provider_status == ProviderStatus.GROQ_PRIMARY
    nvidia_mock.assert_not_called()


def test_nvidia_fallback_on_groq_429():
    """When Groq returns 429, NVIDIA should be used automatically."""
    from unittest.mock import AsyncMock
    gw = AIGateway(config=_cfg())
    gw._groq.complete   = AsyncMock(return_value=_fail("groq", FallbackReason.HTTP_429, 429))
    gw._nvidia.complete = AsyncMock(return_value=_ok("nvidia"))

    result = _run(gw.complete("explain"))

    assert result.success is True
    assert result.provider == "nvidia"
    assert result.is_fallback is True
    assert result.provider_status == ProviderStatus.NVIDIA_FALLBACK


def test_nvidia_fallback_on_groq_timeout():
    """When Groq times out, NVIDIA should be used automatically."""
    from unittest.mock import AsyncMock
    gw = AIGateway(config=_cfg())
    gw._groq.complete   = AsyncMock(return_value=_fail("groq", FallbackReason.TIMEOUT))
    gw._nvidia.complete = AsyncMock(return_value=_ok("nvidia"))

    result = _run(gw.complete("explain"))

    assert result.success is True
    assert result.provider == "nvidia"
    assert result.is_fallback is True


def test_degraded_response_when_both_providers_fail():
    """When both providers fail, a structured degraded response must be returned."""
    from unittest.mock import AsyncMock
    gw = AIGateway(config=_cfg())
    gw._groq.complete   = AsyncMock(return_value=_fail("groq",  FallbackReason.HTTP_429, 429))
    gw._nvidia.complete = AsyncMock(return_value=_fail("nvidia", FallbackReason.HTTP_5XX, 503))

    result = _run(gw.complete("explain"))

    assert result.success is False
    assert result.provider == "none"
    assert result.provider_status == ProviderStatus.DEGRADED
    # Degraded message must exist and be meaningful
    assert len(result.degraded_message) > 10
    # text property must return degraded message
    assert result.text == result.degraded_message


def test_rules_engine_works_without_ai_providers():
    """The deterministic rules engine must work even when all AI providers are unavailable."""
    from rules.rules_engine import RulesEngine
    from config import load_weights

    engine = RulesEngine(load_weights())
    events = [
        {"event_type": "TAB_SWITCH",          "timestamp": 1000},
        {"event_type": "FOCUS_LOSS",           "timestamp": 2000},
        {"event_type": "AI_ASSISTANT_SIGNAL",  "timestamp": 3000},
        {"event_type": "PASTE",                "timestamp": 4000},
    ]
    result = engine.evaluate(events)

    # Score must be positive and deterministic regardless of AI gateway state
    assert result.total_score > 0
    assert result.risk_level.value in {
        "NORMAL", "MONITORING", "ATTENTION", "REVIEW_REQUIRED", "HIGH_PRIORITY_REVIEW"
    }
    # Run again — same events → same score
    result2 = engine.evaluate(events)
    assert result.total_score == result2.total_score
