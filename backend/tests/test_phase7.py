"""
Phase 7 — AI Gateway Tests
=======================================================================
Tests cover:
  - GatewayConfig loading
  - ProviderHealth state machine (healthy → degraded → unhealthy → recovery)
  - ProviderCallResult dataclass
  - FallbackReason classification
  - AIGateway.complete() — all failure scenarios + fallback logic
  - AIGateway health status
  - Groq PRIMARY used on success
  - NVIDIA fallback on: 429, timeout, 5xx, connection error, empty response
  - Both-providers-fail → degraded response
  - Rules Engine unaffected by provider failures
  - Prompt builder
  - Provider restoration after recovery

All tests use mock ProviderClient objects — no real HTTP calls.

Run:
    python -m pytest backend/tests/test_phase7.py -v --rootdir=backend
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Path setup so we can import from backend/app without installing ──────────
_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

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

from app.services.ai_gateway.config import GatewayConfig, load_gateway_config
from app.services.ai_gateway.health import ProviderHealth, HealthState
from app.services.ai_gateway.providers import (
    FallbackReason,
    ProviderCallResult,
    _classify_http_error,
    _extract_content,
    _extract_usage,
)
from app.services.ai_gateway.gateway import (
    AIGateway,
    AIGatewayResponse,
    ProviderStatus,
    _build_messages,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _success(provider: str = "groq") -> ProviderCallResult:
    return ProviderCallResult(
        success=True,
        provider=provider,
        request_id=str(uuid.uuid4()),
        content="This session shows behavioral patterns that warrant teacher review.",
        model="llama3-8b-8192",
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=450,
        http_status=200,
    )


def _failure(
    provider: str = "groq",
    reason: FallbackReason = FallbackReason.HTTP_429,
    http_status: int | None = 429,
) -> ProviderCallResult:
    return ProviderCallResult(
        success=False,
        provider=provider,
        request_id=str(uuid.uuid4()),
        latency_ms=50,
        http_status=http_status,
        failure_reason=reason,
        error_detail="test failure",
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


def _make_gateway() -> tuple[AIGateway, AsyncMock, AsyncMock]:
    """Return (gateway, groq_mock, nvidia_mock) with both clients replaced."""
    gw = AIGateway(config=_cfg())
    groq_mock  = AsyncMock(return_value=_success("groq"))
    nvidia_mock = AsyncMock(return_value=_success("nvidia"))
    gw._groq.complete  = groq_mock
    gw._nvidia.complete = nvidia_mock
    return gw, groq_mock, nvidia_mock


# ─────────────────────────────────────────────────────────────────────────────
# Group 1 — GatewayConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestGatewayConfig:
    def test_config_is_frozen(self):
        cfg = _cfg()
        with pytest.raises((AttributeError, TypeError)):
            cfg.groq_api_key = "new"  # type: ignore[misc]

    @pytest.mark.skip(reason="Requires pydantic_settings — run in Docker with Python 3.11")
    def test_load_gateway_config_returns_dataclass(self):
        cfg = load_gateway_config()
        assert isinstance(cfg, GatewayConfig)

    @pytest.mark.skip(reason="Requires pydantic_settings — run in Docker with Python 3.11")
    def test_groq_key_set_from_env(self):
        cfg = load_gateway_config()
        assert cfg.groq_api_key == "test-groq-key"

    @pytest.mark.skip(reason="Requires pydantic_settings — run in Docker with Python 3.11")
    def test_nvidia_key_set_from_env(self):
        cfg = load_gateway_config()
        assert cfg.nvidia_api_key == "test-nvidia-key"

    def test_groq_model_set(self):
        cfg = _cfg()
        assert cfg.groq_model == "llama3-8b-8192"

    def test_nvidia_model_set(self):
        cfg = _cfg()
        assert cfg.nvidia_model == "meta/llama3-8b-instruct"

    def test_recovery_threshold_positive(self):
        cfg = _cfg()
        assert cfg.recovery_threshold > 0


# ─────────────────────────────────────────────────────────────────────────────
# Group 2 — ProviderHealth
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderHealth:
    def test_initial_state_healthy(self):
        h = ProviderHealth("groq")
        assert h.state == HealthState.HEALTHY
        assert h.is_available

    def test_single_failure_stays_degraded(self):
        h = ProviderHealth("groq", failure_threshold=2, open_threshold=3)
        _run(h.record_failure())
        # 1 failure < failure_threshold=2 → still HEALTHY
        assert h.state == HealthState.HEALTHY

    def test_failure_threshold_transitions_to_degraded(self):
        h = ProviderHealth("groq", failure_threshold=2, open_threshold=4)
        _run(h.record_failure())
        _run(h.record_failure())
        assert h.state == HealthState.DEGRADED
        assert h.is_available  # degraded is still tried

    def test_open_threshold_transitions_to_unhealthy(self):
        h = ProviderHealth("groq", failure_threshold=1, open_threshold=2)
        _run(h.record_failure())
        _run(h.record_failure())
        assert h.state == HealthState.UNHEALTHY
        assert not h.is_available  # circuit open

    def test_recovery_after_successes(self):
        h = ProviderHealth("groq", failure_threshold=1, open_threshold=2, recovery_threshold=2)
        _run(h.record_failure())
        _run(h.record_failure())
        assert h.state == HealthState.UNHEALTHY
        _run(h.record_success())
        _run(h.record_success())
        assert h.state == HealthState.HEALTHY

    def test_success_resets_consecutive_failures(self):
        h = ProviderHealth("groq", failure_threshold=2, open_threshold=3)
        _run(h.record_failure())
        assert h.consecutive_failures == 1
        _run(h.record_success())
        assert h.consecutive_failures == 0

    def test_reset_returns_to_healthy(self):
        h = ProviderHealth("groq", failure_threshold=1, open_threshold=1)
        _run(h.record_failure())
        assert h.state == HealthState.UNHEALTHY
        h.reset()
        assert h.state == HealthState.HEALTHY
        assert h.is_available

    def test_to_dict_contains_provider_name(self):
        h = ProviderHealth("groq")
        d = h.to_dict()
        assert d["provider"] == "groq"

    def test_to_dict_contains_state(self):
        h = ProviderHealth("nvidia")
        d = h.to_dict()
        assert "state" in d

    def test_consecutive_successes_tracked(self):
        h = ProviderHealth("groq")
        _run(h.record_success())
        _run(h.record_success())
        assert h.consecutive_successes == 2


# ─────────────────────────────────────────────────────────────────────────────
# Group 3 — Provider helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderHelpers:
    def test_extract_content_valid(self):
        data = {"choices": [{"message": {"content": "Hello world"}}]}
        assert _extract_content(data) == "Hello world"

    def test_extract_content_empty_choices(self):
        assert _extract_content({}) == ""

    def test_extract_content_none_content(self):
        data = {"choices": [{"message": {"content": None}}]}
        assert _extract_content(data) == ""

    def test_extract_usage_present(self):
        data = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        pt, ct = _extract_usage(data)
        assert pt == 10 and ct == 20

    def test_extract_usage_missing(self):
        pt, ct = _extract_usage({})
        assert pt is None and ct is None

    def test_fallback_reason_enum_values(self):
        assert FallbackReason.HTTP_429.value == "http_429"
        assert FallbackReason.TIMEOUT.value == "timeout"
        assert FallbackReason.HTTP_5XX.value == "http_5xx"

    def test_provider_call_result_success_fields(self):
        r = _success("groq")
        assert r.success is True
        assert r.provider == "groq"
        assert len(r.content) > 0

    def test_provider_call_result_failure_fields(self):
        r = _failure("groq", FallbackReason.HTTP_429, 429)
        assert r.success is False
        assert r.failure_reason == FallbackReason.HTTP_429
        assert r.http_status == 429

    def test_build_messages_includes_system(self):
        msgs = _build_messages("user prompt", "system prompt")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "system prompt"

    def test_build_messages_includes_user(self):
        msgs = _build_messages("user prompt", None)
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "user prompt"

    def test_build_messages_default_system_prompt(self):
        msgs = _build_messages("hello", None)
        # Should still have a system message (default)
        assert any(m["role"] == "system" for m in msgs)


# ─────────────────────────────────────────────────────────────────────────────
# Group 4 — AIGateway primary / fallback logic
# ─────────────────────────────────────────────────────────────────────────────

class TestAIGatewayProviderLogic:
    def test_groq_success_returns_groq_provider(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        result = _run(
            gw.complete("explain this session")
        )
        assert result.success is True
        assert result.provider == "groq"
        assert result.is_fallback is False
        nvidia_mock.assert_not_called()

    def test_groq_success_uses_primary_status(self):
        gw, groq_mock, _ = _make_gateway()
        result = _run(
            gw.complete("explain this session")
        )
        assert result.provider_status == ProviderStatus.GROQ_PRIMARY

    def test_groq_429_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.HTTP_429, 429)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"
        assert result.is_fallback is True
        assert result.provider_status == ProviderStatus.NVIDIA_FALLBACK

    def test_groq_timeout_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.TIMEOUT, None)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"
        assert result.is_fallback is True

    def test_groq_5xx_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.HTTP_5XX, 503)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"

    def test_groq_connection_error_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.CONNECTION_ERROR, None)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"

    def test_groq_empty_response_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.EMPTY_RESPONSE, 200)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"

    def test_groq_token_limit_uses_nvidia_fallback(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.TOKEN_LIMIT, 400)
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        assert result.success is True
        assert result.provider == "nvidia"

    def test_both_providers_fail_returns_degraded(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value  = _failure("groq",   FallbackReason.HTTP_429, 429)
        nvidia_mock.return_value = _failure("nvidia", FallbackReason.HTTP_5XX, 500)
        result = _run(
            gw.complete("explain")
        )
        assert result.success is False
        assert result.provider == "none"
        assert result.provider_status == ProviderStatus.DEGRADED
        assert len(result.degraded_message) > 0

    def test_degraded_message_mentions_evidence(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value  = _failure("groq",   FallbackReason.HTTP_429, 429)
        nvidia_mock.return_value = _failure("nvidia", FallbackReason.HTTP_5XX, 500)
        result = _run(
            gw.complete("explain")
        )
        assert "evidence" in result.degraded_message.lower() or \
               "risk" in result.degraded_message.lower() or \
               "unavailable" in result.degraded_message.lower()

    def test_degraded_response_text_property(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value  = _failure("groq",   FallbackReason.TIMEOUT, None)
        nvidia_mock.return_value = _failure("nvidia", FallbackReason.TIMEOUT, None)
        result = _run(
            gw.complete("explain")
        )
        assert result.text == result.degraded_message

    def test_success_text_property_returns_content(self):
        gw, groq_mock, _ = _make_gateway()
        result = _run(
            gw.complete("explain")
        )
        assert result.text == result.content

    def test_groq_circuit_open_skips_groq(self):
        """When Groq health is UNHEALTHY (circuit open), skip directly to NVIDIA."""
        gw, groq_mock, nvidia_mock = _make_gateway()
        gw._groq_health._state = HealthState.UNHEALTHY
        nvidia_mock.return_value = _success("nvidia")
        result = _run(
            gw.complete("explain")
        )
        groq_mock.assert_not_called()
        assert result.provider == "nvidia"

    def test_groq_recovers_after_successes(self):
        """After enough successes, Groq health returns to HEALTHY."""
        h = ProviderHealth("groq", failure_threshold=1, open_threshold=2, recovery_threshold=2)
        _run(h.record_failure())
        _run(h.record_failure())
        assert h.state == HealthState.UNHEALTHY
        _run(h.record_success())
        _run(h.record_success())
        assert h.state == HealthState.HEALTHY
        assert h.is_available

    def test_request_id_present_in_response(self):
        gw, groq_mock, _ = _make_gateway()
        result = _run(
            gw.complete("explain")
        )
        assert result.request_id and len(result.request_id) > 0

    def test_latency_ms_in_response(self):
        gw, groq_mock, _ = _make_gateway()
        result = _run(
            gw.complete("explain")
        )
        assert isinstance(result.latency_ms, int)

    def test_content_not_empty_on_success(self):
        gw, groq_mock, _ = _make_gateway()
        result = _run(
            gw.complete("explain")
        )
        assert len(result.content) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Group 5 — Gateway health status
# ─────────────────────────────────────────────────────────────────────────────

class TestGatewayHealthStatus:
    def test_health_status_has_groq_key(self):
        gw = AIGateway(config=_cfg())
        status = _run(gw.health_status())
        assert "groq" in status

    def test_health_status_has_nvidia_key(self):
        gw = AIGateway(config=_cfg())
        status = _run(gw.health_status())
        assert "nvidia" in status

    def test_health_status_has_active_primary(self):
        gw = AIGateway(config=_cfg())
        status = _run(gw.health_status())
        assert "active_primary" in status

    def test_health_status_initial_primary_is_groq(self):
        gw = AIGateway(config=_cfg())
        status = _run(gw.health_status())
        assert status["active_primary"] == "groq"

    def test_reset_health_restores_groq(self):
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value = _failure("groq", FallbackReason.HTTP_429, 429)
        nvidia_mock.return_value = _success("nvidia")
        # Force Groq into unhealthy state
        for _ in range(3):
            _run(
                gw._groq_health.record_failure()
            )
        assert gw._groq_health.state == HealthState.UNHEALTHY
        gw.reset_health()
        assert gw._groq_health.state == HealthState.HEALTHY


# ─────────────────────────────────────────────────────────────────────────────
# Group 6 — Rules Engine independence (deterministic even without AI)
# ─────────────────────────────────────────────────────────────────────────────

class TestRulesEngineIndependence:
    """
    Critical requirement: the deterministic Rules Engine MUST function
    correctly even when all AI providers are unavailable.
    """

    def test_rules_engine_works_without_ai_providers(self):
        """Pure deterministic import — no AI dependency."""
        import sys, os
        _MCP = os.path.join(os.path.dirname(__file__), "..", "..", "mcp")
        if _MCP not in sys.path:
            sys.path.insert(0, _MCP)
        from rules.rules_engine import RulesEngine
        from config import load_weights
        engine = RulesEngine(load_weights())
        result = engine.evaluate([{"event_type": "TAB_SWITCH", "timestamp": 1000}])
        assert result.total_score > 0
        assert result.risk_level is not None

    def test_rules_engine_score_is_deterministic(self):
        import sys, os
        _MCP = os.path.join(os.path.dirname(__file__), "..", "..", "mcp")
        if _MCP not in sys.path:
            sys.path.insert(0, _MCP)
        from rules.rules_engine import RulesEngine
        from config import load_weights
        events = [
            {"event_type": "TAB_SWITCH", "timestamp": 1000},
            {"event_type": "FOCUS_LOSS",  "timestamp": 2000},
            {"event_type": "PASTE",       "timestamp": 3000},
        ]
        engine = RulesEngine(load_weights())
        r1 = engine.evaluate(events)
        r2 = engine.evaluate(events)
        assert r1.total_score == r2.total_score

    def test_degraded_gateway_does_not_affect_risk_score(self):
        """Risk score from Rules Engine is independent of AI gateway state."""
        import sys, os
        _MCP = os.path.join(os.path.dirname(__file__), "..", "..", "mcp")
        if _MCP not in sys.path:
            sys.path.insert(0, _MCP)
        from rules.rules_engine import RulesEngine
        from config import load_weights
        engine = RulesEngine(load_weights())
        events = [{"event_type": "AI_ASSISTANT_SIGNAL", "timestamp": 1000}]
        result = engine.evaluate(events)
        # Score should be 25 (AI_ASSISTANT_SIGNAL weight) — regardless of gateway
        assert result.total_score == 25

    def test_both_providers_fail_score_still_deterministic(self):
        """Even with degraded AI response, the risk score is still correct."""
        gw, groq_mock, nvidia_mock = _make_gateway()
        groq_mock.return_value  = _failure("groq",   FallbackReason.HTTP_429, 429)
        nvidia_mock.return_value = _failure("nvidia", FallbackReason.HTTP_5XX, 500)
        ai_result = _run(
            gw.complete("explain")
        )
        # AI result is degraded, but rules engine output is separate
        assert ai_result.success is False

        import sys, os
        _MCP = os.path.join(os.path.dirname(__file__), "..", "..", "mcp")
        if _MCP not in sys.path:
            sys.path.insert(0, _MCP)
        from rules.rules_engine import RulesEngine
        from config import load_weights
        engine = RulesEngine(load_weights())
        score_result = engine.evaluate([{"event_type": "COPY", "timestamp": 1000}])
        assert score_result.total_score == 15   # COPY weight is 15


# ─────────────────────────────────────────────────────────────────────────────
# Group 7 — AIGatewayResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestAIGatewayResponse:
    def test_success_response_fields(self):
        r = AIGatewayResponse(
            success=True,
            provider="groq",
            provider_status=ProviderStatus.GROQ_PRIMARY,
            content="Explanation text.",
            model="llama3-8b-8192",
            is_fallback=False,
            latency_ms=300,
        )
        assert r.success is True
        assert r.provider == "groq"
        assert r.text == "Explanation text."
        assert r.is_fallback is False

    def test_degraded_response_fields(self):
        r = AIGatewayResponse(
            success=False,
            provider="none",
            provider_status=ProviderStatus.DEGRADED,
            degraded_message="Service unavailable.",
            is_fallback=True,
        )
        assert r.success is False
        assert r.text == "Service unavailable."

    def test_fallback_response_is_fallback_true(self):
        r = AIGatewayResponse(
            success=True,
            provider="nvidia",
            provider_status=ProviderStatus.NVIDIA_FALLBACK,
            content="Fallback explanation.",
            is_fallback=True,
        )
        assert r.is_fallback is True
        assert r.provider == "nvidia"

    def test_request_id_auto_generated(self):
        r = AIGatewayResponse(
            success=True, provider="groq",
            provider_status=ProviderStatus.GROQ_PRIMARY,
        )
        assert r.request_id and len(r.request_id) == 36

    def test_provider_status_enum_values(self):
        assert ProviderStatus.GROQ_PRIMARY.value == "groq_primary"
        assert ProviderStatus.NVIDIA_FALLBACK.value == "nvidia_fallback"
        assert ProviderStatus.DEGRADED.value == "degraded"
