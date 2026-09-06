"""
Explanation Orchestrator Service

Wires together:
  1. MCP create_incident_summary  → structured evidence + risk summary
  2. RAG get_policy_context       → retrieved (not invented) policy text
  3. AI Gateway                   → Groq PRIMARY / NVIDIA FALLBACK explanation
  4. Prompt Builder               → validated, structured prompt

Rules enforced:
  - Evidence section is populated from MCP (deterministic rules output)
  - Policy section is populated from RAG (retrieved documents only)
  - AI produces INFERENCE only — never determines guilt
  - If MCP is unavailable: evidence from raw events only, no incident_summary
  - If RAG is unavailable: fallback default policy text used
  - If AI is unavailable: degraded response returned, risk score still accurate
  - The `teacher_disclaimer` field is always populated

IMPORTANT:
  This service NEVER stores results directly — that is the caller's responsibility.
  All I/O is async. No blocking calls.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.ai_gateway.gateway import AIGateway
from app.services.ai_gateway.prompt_builder import (
    FORBIDDEN_PHRASES,
    LABEL_EVIDENCE,
    LABEL_INFERENCE,
    LABEL_POLICY,
    REQUIRED_DISCLAIMER,
    IncidentPrompt,
    build_incident_prompt,
)

logger = structlog.get_logger(__name__)

# Default policy text when RAG is unavailable
_DEFAULT_POLICY = (
    "[DEFAULT POLICY — RAG unavailable]\n"
    "AI assistants are prohibited during closed-resource examinations. "
    "The use of any AI writing assistant, code assistant, or AI-powered tool "
    "constitutes a violation of academic integrity policy. "
    "The teacher makes the final determination."
)

# Disclaimer that must always appear in the final explanation
_TEACHER_DISCLAIMER = "The final determination belongs to the reviewing teacher."


@dataclass
class ExplanationResult:
    """Full output from the explanation orchestrator."""
    request_id: str                     = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str                     = ""
    explanation: str                    = ""
    teacher_disclaimer: str             = _TEACHER_DISCLAIMER
    provider: str                       = "none"
    is_fallback: bool                   = False
    success: bool                       = False
    degraded: bool                      = False
    risk_score: int                     = 0
    risk_level: str                     = "UNKNOWN"
    mcp_summary_available: bool         = False
    rag_policy_available: bool          = False
    latency_ms: int                     = 0
    # Labels present in explanation text
    has_evidence_label: bool            = False
    has_policy_label: bool              = False
    has_inference_label: bool           = False
    has_disclaimer: bool                = False
    # Validation
    forbidden_phrase_detected: bool     = False
    forbidden_phrase: str               = ""

    def validate_output(self) -> None:
        """
        Post-generation quality check.
        Sets forbidden_phrase_detected if AI violated the no-verdict rule.
        Sets has_* flags based on actual explanation content.
        """
        text_lower = self.explanation.lower()

        for phrase in FORBIDDEN_PHRASES:
            if phrase in text_lower:
                self.forbidden_phrase_detected = True
                self.forbidden_phrase = phrase
                logger.warning(
                    "forbidden_phrase_in_explanation",
                    request_id=self.request_id,
                    phrase=phrase,
                    provider=self.provider,
                )
                break

        self.has_evidence_label  = LABEL_EVIDENCE.lower()  in text_lower
        self.has_policy_label    = LABEL_POLICY.lower()    in text_lower
        self.has_inference_label = LABEL_INFERENCE.lower() in text_lower
        self.has_disclaimer      = REQUIRED_DISCLAIMER.lower() in text_lower


class ExplanationOrchestrator:
    """
    Combines MCP evidence, RAG policy, and AI Gateway into a
    structured, explainable incident summary.

    Designed to be imported as a singleton or created per-request.
    All dependencies are injected — makes testing straightforward.
    """

    def __init__(
        self,
        gateway: AIGateway | None = None,
        mcp_client=None,
        rag_client=None,
    ) -> None:
        self._gateway   = gateway
        self._mcp       = mcp_client   # app.services.mcp_client module or mock
        self._rag       = rag_client   # app.services.rag_client module or mock

    # ── Public API ────────────────────────────────────────────────────────────

    async def explain(
        self,
        session_id: str,
        events: list[dict[str, Any]],
        risk_score: int,
        risk_level: str,
        exam_title: str = "Examination",
        exam_id: str | None = None,
        institution: str | None = None,
        student_id: str | None = None,
        ai_detection_signals: list[dict[str, Any]] | None = None,
        correlation_timeline: list[dict[str, Any]] | None = None,
    ) -> ExplanationResult:
        """
        Full pipeline:
          1. Fetch MCP incident summary (graceful degradation if unavailable)
          2. Fetch RAG policy context (graceful degradation if unavailable)
          3. Build structured prompt
          4. Call AI Gateway (Groq → NVIDIA → degraded)
          5. Validate output (no forbidden phrases, required labels present)
          6. Return ExplanationResult

        The deterministic risk_score is ALWAYS included regardless of AI availability.
        """
        started = time.monotonic()
        result = ExplanationResult(
            session_id=session_id,
            risk_score=risk_score,
            risk_level=risk_level,
        )

        # ── Step 1: MCP incident summary ──────────────────────────────────────
        incident_summary = await self._fetch_incident_summary(
            session_id=session_id,
            events=events,
            risk_score=risk_score,
            risk_level=risk_level,
            exam_title=exam_title,
            student_id=student_id or "",
            result=result,
        )

        # ── Step 2: RAG policy context ────────────────────────────────────────
        policy_context = await self._fetch_policy_context(
            exam_id=exam_id,
            institution=institution,
            result=result,
        )

        # ── Step 3: Build structured prompt ───────────────────────────────────
        prompt_obj: IncidentPrompt = build_incident_prompt(
            session_id=session_id,
            exam_title=exam_title,
            risk_score=risk_score,
            risk_level=risk_level,
            events=events,
            incident_summary=incident_summary,
            policy_context=policy_context,
            ai_detection_signals=ai_detection_signals,
            correlation_timeline=correlation_timeline,
        )

        validation_issues = prompt_obj.validate()
        if validation_issues:
            logger.warning(
                "prompt_validation_issues",
                session_id=session_id,
                issues=validation_issues,
            )

        prompt_text = prompt_obj.build()

        # ── Step 4: AI Gateway ────────────────────────────────────────────────
        if self._gateway is None:
            from app.services.ai_gateway import get_gateway
            self._gateway = get_gateway()

        try:
            ai_result = await self._gateway.complete(
                prompt=prompt_text,
                max_tokens=1200,
                temperature=0.2,
            )
        except Exception as exc:
            logger.error(
                "explanation_gateway_error",
                session_id=session_id,
                error=str(exc),
            )
            result.explanation = _build_degraded_explanation(risk_score, risk_level, events)
            result.degraded = True
            result.success  = False
            result.provider = "none"
            result.latency_ms = int((time.monotonic() - started) * 1000)
            result.validate_output()
            return result

        # ── Step 5: Populate result ───────────────────────────────────────────
        result.provider     = ai_result.provider
        result.is_fallback  = ai_result.is_fallback
        result.success      = ai_result.success
        result.degraded     = not ai_result.success
        result.latency_ms   = int((time.monotonic() - started) * 1000)

        if ai_result.success and ai_result.content:
            result.explanation = _ensure_disclaimer(ai_result.content)
        else:
            result.explanation = _build_degraded_explanation(risk_score, risk_level, events)

        # ── Step 6: Output validation ─────────────────────────────────────────
        result.validate_output()

        if result.forbidden_phrase_detected:
            # Sanitise — replace explanation with safe fallback
            logger.error(
                "explanation_sanitised_forbidden_phrase",
                session_id=session_id,
                phrase=result.forbidden_phrase,
            )
            result.explanation = _build_safe_fallback(risk_score, risk_level)

        logger.info(
            "explanation_complete",
            session_id=session_id,
            provider=result.provider,
            success=result.success,
            has_disclaimer=result.has_disclaimer,
            latency_ms=result.latency_ms,
        )

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _fetch_incident_summary(
        self,
        session_id: str,
        events: list[dict[str, Any]],
        risk_score: int,
        risk_level: str,
        exam_title: str,
        student_id: str,
        result: ExplanationResult,
    ) -> str:
        if self._mcp is None:
            return ""
        try:
            summary_data = await self._mcp.create_incident_summary(
                session_id=session_id,
                events=events,
                risk_score=risk_score,
                risk_level=risk_level,
                exam_title=exam_title,
                student_id=student_id,
            )
            text = summary_data.get("summary") or summary_data.get("incident_summary", "")
            result.mcp_summary_available = bool(text)
            return text
        except Exception as exc:
            logger.warning(
                "mcp_incident_summary_failed",
                session_id=session_id,
                error=str(exc),
            )
            return ""

    async def _fetch_policy_context(
        self,
        exam_id: str | None,
        institution: str | None,
        result: ExplanationResult,
    ) -> str:
        if self._rag is None:
            result.rag_policy_available = False
            return _DEFAULT_POLICY
        try:
            ctx = await self._rag.get_policy_context(
                exam_id=exam_id,
                institution=institution,
            )
            if ctx:
                result.rag_policy_available = True
                return ctx
            result.rag_policy_available = False
            return _DEFAULT_POLICY
        except Exception as exc:
            logger.warning(
                "rag_policy_context_failed",
                error=str(exc),
            )
            result.rag_policy_available = False
            return _DEFAULT_POLICY


# ── Text helpers ──────────────────────────────────────────────────────────────

def _ensure_disclaimer(text: str) -> str:
    """Append disclaimer if the AI omitted it."""
    if REQUIRED_DISCLAIMER.lower() not in text.lower():
        return text.rstrip() + f"\n\n{_TEACHER_DISCLAIMER}"
    return text


def _build_degraded_explanation(
    risk_score: int,
    risk_level: str,
    events: list[dict[str, Any]],
) -> str:
    """
    Structured fallback when AI is unavailable.
    Always includes the required disclaimer and evidence summary.
    """
    event_types = [e.get("event_type", e.get("type", "?")) for e in events[:10]]
    type_summary = ", ".join(set(event_types)) if event_types else "none recorded"

    return (
        f"[{LABEL_EVIDENCE}]\n"
        f"Risk Score: {risk_score}/100 — Level: {risk_level}\n"
        f"Event types observed: {type_summary}\n\n"
        f"[{LABEL_POLICY}]\n"
        "AI assistants and external resources are prohibited "
        "during closed-resource examinations per default policy.\n\n"
        f"[{LABEL_INFERENCE}]\n"
        "AI explanation is temporarily unavailable. "
        "The deterministic risk score above is accurate and unaffected. "
        "Please review the behavioral evidence timeline directly.\n\n"
        f"{_TEACHER_DISCLAIMER}"
    )


def _build_safe_fallback(risk_score: int, risk_level: str) -> str:
    """Used when the AI output contained a forbidden phrase."""
    return (
        f"[{LABEL_EVIDENCE}]\n"
        f"Risk Score: {risk_score}/100 — Level: {risk_level}\n\n"
        f"[{LABEL_POLICY}]\n"
        "Standard exam integrity policy applies.\n\n"
        f"[{LABEL_INFERENCE}]\n"
        "The AI-generated explanation was removed because it contained "
        "language that does not comply with platform policy (no verdicts allowed). "
        "Please review the behavioral evidence timeline directly.\n\n"
        f"{_TEACHER_DISCLAIMER}"
    )
