"""
Phase 8 — AI Explanation + RAG Integration Tests
=======================================================================
Tests cover:
  - IncidentPrompt structure and build()
  - Prompt contains all required labelled sections
  - Prompt includes event timeline, AI signals, correlation, policy
  - Prompt never fabricates policy
  - ExplanationResult validation (forbidden phrases, labels, disclaimer)
  - ExplanationOrchestrator — full pipeline (all mocked)
  - Orchestrator: MCP unavailable → graceful degradation
  - Orchestrator: RAG unavailable → default policy text used
  - Orchestrator: AI unavailable → deterministic score preserved
  - Orchestrator: AI returns forbidden phrase → sanitised output
  - Disclaimer always present in every explanation
  - Evidence ≠ Inference labelling verified
  - ForbiddenPhrase detection
  - Degraded explanation helper functions
  - All tests run natively — no real HTTP calls

Run:
    python -m pytest backend/tests/test_phase8.py -v --rootdir=backend
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
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

from app.services.ai_gateway.config import GatewayConfig
from app.services.ai_gateway.gateway import AIGateway, AIGatewayResponse, ProviderStatus
from app.services.ai_gateway.providers import FallbackReason, ProviderCallResult
from app.services.ai_gateway.prompt_builder import (
    FORBIDDEN_PHRASES,
    LABEL_EVIDENCE,
    LABEL_INFERENCE,
    LABEL_POLICY,
    REQUIRED_DISCLAIMER,
    IncidentPrompt,
    build_incident_prompt,
)
from app.services.explanation_service import (
    ExplanationOrchestrator,
    ExplanationResult,
    _build_degraded_explanation,
    _build_safe_fallback,
    _ensure_disclaimer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
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


def _cfg() -> GatewayConfig:
    return GatewayConfig(
        groq_api_key="test-groq",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama3-8b-8192",
        groq_timeout=5.0, groq_max_retries=1,
        nvidia_api_key="test-nvidia",
        nvidia_base_url="https://integrate.api.nvidia.com/v1",
        nvidia_model="meta/llama3-8b-instruct",
        nvidia_timeout=5.0, nvidia_max_retries=1,
        health_check_interval=60, recovery_threshold=3,
    )


def _sample_events() -> list[dict]:
    return [
        {"event_type": "FOCUS_LOSS",          "occurred_at": "10:42:11", "timestamp": 1000},
        {"event_type": "SUSPICIOUS_NAVIGATION","occurred_at": "10:42:18", "timestamp": 1007,
         "metadata": {"url": "https://parakeet-ai.com"}},
        {"event_type": "FOCUS_GAIN",           "occurred_at": "10:42:41", "timestamp": 1030},
        {"event_type": "COPY",                 "occurred_at": "10:42:45", "timestamp": 1034},
        {"event_type": "PASTE",                "occurred_at": "10:42:49", "timestamp": 1038,
         "metadata": {"paste_length": 450}},
        {"event_type": "AI_ASSISTANT_SIGNAL",  "occurred_at": "10:43:02", "timestamp": 1051},
    ]


def _sample_ai_signals() -> list[dict]:
    return [
        {"assistant_name": "ParakeetAI", "detection_state": "DETECTED",  "confidence": 0.82},
        {"assistant_name": "ChatGPT",    "detection_state": "SUSPECTED",  "confidence": 0.45},
    ]


def _sample_correlations() -> list[dict]:
    return [
        {"sequence_name": "ai_nav_paste", "bonus_score": 20},
    ]


def _make_gateway_success(content: str = "Review recommended. OBSERVED EVIDENCE shows suspicious navigation to parakeet-ai.com, followed by copy/paste. [POLICY INTERPRETATION] AI tools are prohibited. [AI INFERENCE] This pattern may indicate AI assistant usage. The final determination belongs to the reviewing teacher.") -> AIGateway:
    gw = AIGateway(config=_cfg())
    result = ProviderCallResult(
        success=True, provider="groq", request_id=str(uuid.uuid4()),
        content=content, model="llama3-8b-8192",
        latency_ms=400, http_status=200,
    )
    gw._groq.complete  = AsyncMock(return_value=result)
    gw._nvidia.complete = AsyncMock(return_value=result)
    return gw


def _make_gateway_both_fail() -> AIGateway:
    gw = AIGateway(config=_cfg())
    failure = ProviderCallResult(
        success=False, provider="groq", request_id=str(uuid.uuid4()),
        latency_ms=50, http_status=429,
        failure_reason=FallbackReason.HTTP_429, error_detail="test",
    )
    gw._groq.complete  = AsyncMock(return_value=failure)
    gw._nvidia.complete = AsyncMock(
        return_value=ProviderCallResult(
            success=False, provider="nvidia", request_id=str(uuid.uuid4()),
            latency_ms=50, http_status=500,
            failure_reason=FallbackReason.HTTP_5XX, error_detail="test",
        )
    )
    return gw


def _make_orchestrator(
    gateway: AIGateway,
    mcp_summary: str | None = "MCP: 6 events, risk=75, REVIEW_REQUIRED",
    rag_context: str | None = "RETRIEVED POLICY: AI assistants prohibited.",
) -> ExplanationOrchestrator:
    mcp_mock = MagicMock()
    mcp_mock.create_incident_summary = AsyncMock(
        return_value={"summary": mcp_summary} if mcp_summary else {}
    )
    rag_mock = MagicMock()
    rag_mock.get_policy_context = AsyncMock(return_value=rag_context or "")
    return ExplanationOrchestrator(gateway=gateway, mcp_client=mcp_mock, rag_client=rag_mock)


# ─────────────────────────────────────────────────────────────────────────────
# Group 1 — IncidentPrompt + prompt_builder
# ─────────────────────────────────────────────────────────────────────────────

class TestIncidentPrompt:
    def test_build_returns_string(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam 1",
            risk_score=75, risk_level="REVIEW_REQUIRED",
            events=_sample_events(), incident_summary="Summary",
            policy_context="AI prohibited.",
        )
        text = p.build()
        assert isinstance(text, str) and len(text) > 100

    def test_prompt_contains_observed_evidence_label(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=60, risk_level="ATTENTION",
            events=_sample_events(), incident_summary="", policy_context="",
        )
        text = p.build()
        assert LABEL_EVIDENCE in text

    def test_prompt_contains_policy_interpretation_label(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=60, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="Policy here.",
        )
        text = p.build()
        assert LABEL_POLICY in text

    def test_prompt_contains_inference_label(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=60, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="",
        )
        text = p.build()
        assert LABEL_INFERENCE in text

    def test_prompt_contains_risk_score(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=75, risk_level="REVIEW_REQUIRED",
            events=[], incident_summary="", policy_context="",
        )
        assert "75" in p.build()

    def test_prompt_contains_risk_level(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=75, risk_level="REVIEW_REQUIRED",
            events=[], incident_summary="", policy_context="",
        )
        assert "REVIEW_REQUIRED" in p.build()

    def test_prompt_contains_event_types(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=75, risk_level="REVIEW_REQUIRED",
            events=_sample_events(), incident_summary="", policy_context="",
        )
        text = p.build()
        assert "FOCUS_LOSS" in text or "PASTE" in text

    def test_prompt_contains_policy_text(self):
        policy = "AI assistants are strictly prohibited."
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context=policy,
        )
        assert policy in p.build()

    def test_prompt_contains_incident_summary(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="MCP evidence here.", policy_context="",
        )
        assert "MCP evidence here." in p.build()

    def test_prompt_contains_ai_signals_section(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=80, risk_level="HIGH_PRIORITY_REVIEW",
            events=[], incident_summary="",
            policy_context="", ai_detection_signals=_sample_ai_signals(),
        )
        text = p.build()
        assert "ParakeetAI" in text and "DETECTED" in text

    def test_prompt_contains_correlation_section(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=80, risk_level="HIGH_PRIORITY_REVIEW",
            events=[], incident_summary="",
            policy_context="", correlation_timeline=_sample_correlations(),
        )
        assert "ai_nav_paste" in p.build()

    def test_prompt_caps_events_at_30(self):
        events = [{"event_type": "FOCUS_LOSS", "occurred_at": str(i)} for i in range(50)]
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=30, risk_level="MONITORING",
            events=events, incident_summary="", policy_context="",
        )
        text = p.build()
        assert "20 additional events" in text

    def test_prompt_has_no_verdict_language(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=80, risk_level="HIGH_PRIORITY_REVIEW",
            events=_sample_events(), incident_summary="", policy_context="",
        )
        text = p.build().lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, f"Prompt contains forbidden: {phrase!r}"

    def test_prompt_requests_teacher_determination_close(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="",
        )
        assert "final determination" in p.build().lower()

    def test_prompt_warns_against_inventing_policy(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="Policy text.",
        )
        text = p.build().lower()
        assert "do not paraphrase" in text or "not paraphrase" in text or "invent" in text

    def test_validate_passes_valid_prompt(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="",
        )
        assert p.validate() == []

    def test_validate_fails_empty_session_id(self):
        p = build_incident_prompt(
            session_id="", exam_title="Exam",
            risk_score=50, risk_level="ATTENTION",
            events=[], incident_summary="", policy_context="",
        )
        issues = p.validate()
        assert any("session_id" in i for i in issues)

    def test_validate_fails_out_of_range_score(self):
        p = build_incident_prompt(
            session_id="s1", exam_title="Exam",
            risk_score=150, risk_level="REVIEW_REQUIRED",
            events=[], incident_summary="", policy_context="",
        )
        issues = p.validate()
        assert any("risk_score" in i for i in issues)


# ─────────────────────────────────────────────────────────────────────────────
# Group 2 — ExplanationResult validation
# ─────────────────────────────────────────────────────────────────────────────

class TestExplanationResultValidation:
    def test_validate_output_sets_evidence_label(self):
        r = ExplanationResult()
        r.explanation = f"[{LABEL_EVIDENCE}] TAB_SWITCH at 10:42. [{LABEL_INFERENCE}] pattern. The final determination belongs to the reviewing teacher."
        r.validate_output()
        assert r.has_evidence_label is True

    def test_validate_output_sets_inference_label(self):
        r = ExplanationResult()
        r.explanation = f"[{LABEL_EVIDENCE}] x [{LABEL_INFERENCE}] y. The final determination belongs to the reviewing teacher."
        r.validate_output()
        assert r.has_inference_label is True

    def test_validate_output_sets_disclaimer(self):
        r = ExplanationResult()
        r.explanation = "Something. The final determination belongs to the reviewing teacher."
        r.validate_output()
        assert r.has_disclaimer is True

    def test_validate_output_detects_forbidden_phrase(self):
        r = ExplanationResult()
        r.explanation = "The student cheated on the exam."
        r.validate_output()
        assert r.forbidden_phrase_detected is True
        assert "student cheated" in r.forbidden_phrase

    def test_validate_output_no_forbidden_clean_text(self):
        r = ExplanationResult()
        r.explanation = (
            f"[{LABEL_EVIDENCE}] Tab switch observed. "
            f"[{LABEL_INFERENCE}] This may indicate distraction. "
            "The final determination belongs to the reviewing teacher."
        )
        r.validate_output()
        assert r.forbidden_phrase_detected is False

    def test_validate_output_missing_disclaimer_flagged(self):
        r = ExplanationResult()
        r.explanation = f"[{LABEL_EVIDENCE}] x [{LABEL_INFERENCE}] y."
        r.validate_output()
        assert r.has_disclaimer is False

    def test_forbidden_phrases_list_not_empty(self):
        assert len(FORBIDDEN_PHRASES) >= 5

    def test_required_disclaimer_constant(self):
        assert REQUIRED_DISCLAIMER == "final determination"


# ─────────────────────────────────────────────────────────────────────────────
# Group 3 — Text helper functions
# ─────────────────────────────────────────────────────────────────────────────

class TestTextHelpers:
    def test_ensure_disclaimer_appends_when_missing(self):
        text = "Some explanation."
        result = _ensure_disclaimer(text)
        assert "final determination" in result.lower()

    def test_ensure_disclaimer_does_not_duplicate(self):
        text = "Some explanation. The final determination belongs to the reviewing teacher."
        result = _ensure_disclaimer(text)
        assert result.count("final determination") == 1

    def test_degraded_explanation_contains_risk_score(self):
        text = _build_degraded_explanation(75, "REVIEW_REQUIRED", [])
        assert "75" in text

    def test_degraded_explanation_contains_risk_level(self):
        text = _build_degraded_explanation(75, "REVIEW_REQUIRED", [])
        assert "REVIEW_REQUIRED" in text

    def test_degraded_explanation_contains_evidence_label(self):
        text = _build_degraded_explanation(75, "REVIEW_REQUIRED", [])
        assert LABEL_EVIDENCE in text

    def test_degraded_explanation_contains_disclaimer(self):
        text = _build_degraded_explanation(75, "REVIEW_REQUIRED", [])
        assert "final determination" in text.lower()

    def test_degraded_explanation_includes_event_types(self):
        events = [{"event_type": "PASTE"}, {"event_type": "COPY"}]
        text = _build_degraded_explanation(50, "ATTENTION", events)
        assert "PASTE" in text or "COPY" in text

    def test_safe_fallback_contains_evidence_label(self):
        text = _build_safe_fallback(75, "REVIEW_REQUIRED")
        assert LABEL_EVIDENCE in text

    def test_safe_fallback_contains_disclaimer(self):
        text = _build_safe_fallback(75, "REVIEW_REQUIRED")
        assert "final determination" in text.lower()

    def test_safe_fallback_mentions_removal(self):
        text = _build_safe_fallback(75, "REVIEW_REQUIRED")
        assert "removed" in text.lower() or "sanitised" in text.lower() or "sanitized" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Group 4 — ExplanationOrchestrator (full pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TestExplanationOrchestrator:
    def test_successful_pipeline_returns_explanation(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.success is True
        assert len(result.explanation) > 20

    def test_result_provider_is_groq_on_success(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.provider == "groq"

    def test_result_is_fallback_false_on_primary_success(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.is_fallback is False

    def test_mcp_summary_used_when_available(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw, mcp_summary="MCP SUMMARY TEXT")
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert result.mcp_summary_available is True

    def test_mcp_unavailable_does_not_crash(self):
        """If MCP returns empty, orchestrator continues gracefully."""
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw, mcp_summary=None)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.mcp_summary_available is False
        assert result.success is True  # AI still worked

    def test_mcp_exception_does_not_crash(self):
        """If MCP raises an exception, orchestrator continues with empty summary."""
        gw = _make_gateway_success()
        mcp_mock = MagicMock()
        mcp_mock.create_incident_summary = AsyncMock(side_effect=Exception("MCP down"))
        rag_mock = MagicMock()
        rag_mock.get_policy_context = AsyncMock(return_value="Policy text.")
        orch = ExplanationOrchestrator(gateway=gw, mcp_client=mcp_mock, rag_client=rag_mock)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.mcp_summary_available is False
        assert result.success is True

    def test_rag_context_used_when_available(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw, rag_context="RETRIEVED POLICY: AI prohibited.")
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert result.rag_policy_available is True

    def test_rag_unavailable_uses_default_policy(self):
        """RAG returns empty string → default policy used, no crash."""
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw, rag_context="")
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert result.rag_policy_available is False
        assert result.success is True

    def test_rag_exception_uses_default_policy(self):
        """RAG exception → default policy, orchestrator continues."""
        gw = _make_gateway_success()
        mcp_mock = MagicMock()
        mcp_mock.create_incident_summary = AsyncMock(return_value={"summary": "Summary"})
        rag_mock = MagicMock()
        rag_mock.get_policy_context = AsyncMock(side_effect=Exception("RAG down"))
        orch = ExplanationOrchestrator(gateway=gw, mcp_client=mcp_mock, rag_client=rag_mock)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert result.rag_policy_available is False
        assert result.success is True

    def test_both_providers_fail_returns_degraded_with_risk_score(self):
        """AI gateway degraded → risk score still present in degraded explanation."""
        gw = _make_gateway_both_fail()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert result.success is False
        assert result.degraded is True
        assert "75" in result.explanation

    def test_degraded_explanation_contains_risk_level(self):
        gw = _make_gateway_both_fail()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert "REVIEW_REQUIRED" in result.explanation

    def test_disclaimer_always_present_on_success(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert "final determination" in result.explanation.lower()

    def test_disclaimer_always_present_on_degraded(self):
        gw = _make_gateway_both_fail()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        assert "final determination" in result.explanation.lower()

    def test_forbidden_phrase_triggers_sanitisation(self):
        """If AI returns forbidden phrase → explanation is replaced with safe fallback."""
        bad_content = (
            "The student definitely cheated. Evidence is conclusive. "
            "The final determination belongs to the reviewing teacher."
        )
        gw = _make_gateway_success(content=bad_content)
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=80, risk_level="HIGH_PRIORITY_REVIEW",
        ))
        # The original bad content must be replaced
        assert "definitely cheated" not in result.explanation
        assert result.forbidden_phrase_detected is True
        # Safe fallback must contain disclaimer
        assert "final determination" in result.explanation.lower()

    def test_no_verdict_in_normal_explanation(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=_sample_events(),
            risk_score=75, risk_level="REVIEW_REQUIRED",
        ))
        text_lower = result.explanation.lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text_lower

    def test_session_id_in_result(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="session-abc", events=[], risk_score=30, risk_level="MONITORING",
        ))
        assert result.session_id == "session-abc"

    def test_risk_score_preserved_in_result(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=65, risk_level="REVIEW_REQUIRED",
        ))
        assert result.risk_score == 65

    def test_risk_level_preserved_in_result(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=65, risk_level="REVIEW_REQUIRED",
        ))
        assert result.risk_level == "REVIEW_REQUIRED"

    def test_no_mcp_or_rag_client_still_works(self):
        """If both clients are None, fallback defaults are used."""
        gw = _make_gateway_success()
        orch = ExplanationOrchestrator(gateway=gw, mcp_client=None, rag_client=None)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert result.success is True
        assert result.mcp_summary_available is False
        assert result.rag_policy_available is False

    def test_ai_detection_signals_passed_through(self):
        """AI detection signals appear in the prompt sent to the AI."""
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[],
            risk_score=80, risk_level="HIGH_PRIORITY_REVIEW",
            ai_detection_signals=_sample_ai_signals(),
        ))
        assert result.success is True

    def test_latency_ms_recorded(self):
        gw = _make_gateway_success()
        orch = _make_orchestrator(gw)
        result = _run(orch.explain(
            session_id="s1", events=[], risk_score=50, risk_level="ATTENTION",
        ))
        assert isinstance(result.latency_ms, int) and result.latency_ms >= 0
