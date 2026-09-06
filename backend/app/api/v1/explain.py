"""
Explanation API — POST /api/v1/explain

Two endpoints:

1. POST /explain
   Simple: caller supplies pre-built incident_summary + policy_context.
   The AI gateway adds the explanation.

2. POST /explain/full
   Fully orchestrated: fetches MCP incident summary + RAG policy automatically,
   then calls AI Gateway. Recommended for production use.

Both endpoints require teacher role. Students never receive AI explanations.

SECURITY:
  - AI keys never appear in any response.
  - policy_context is labelled as RETRIEVED — not AI-generated.
  - Explanation always ends with teacher-determination disclaimer.
  - Forbidden phrases are detected and sanitised server-side.
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_role
from app.services.ai_gateway import gateway, AIGatewayResponse
from app.services.ai_gateway.prompt_builder import (
    LABEL_EVIDENCE,
    LABEL_INFERENCE,
    LABEL_POLICY,
    build_incident_prompt,
)
from app.services.explanation_service import ExplanationOrchestrator, ExplanationResult

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/explain", tags=["Explanation"])


# ── Shared schemas ────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    """Simple explain — caller provides pre-fetched context."""
    session_id: str
    student_id: Optional[str] = None
    exam_title: str = "Examination"
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    events: list[dict[str, Any]] = []
    policy_context: Optional[str] = None
    incident_summary: Optional[str] = None
    ai_detection_signals: list[dict[str, Any]] = []
    correlation_timeline: list[dict[str, Any]] = []


class FullExplainRequest(BaseModel):
    """Full orchestration — service fetches MCP + RAG automatically."""
    session_id: str
    student_id: Optional[str] = None
    exam_title: str = "Examination"
    exam_id: Optional[str] = None
    institution: Optional[str] = None
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    events: list[dict[str, Any]] = []
    ai_detection_signals: list[dict[str, Any]] = []
    correlation_timeline: list[dict[str, Any]] = []


class ExplainResponse(BaseModel):
    session_id: str
    explanation: str
    teacher_disclaimer: str
    provider: str
    is_fallback: bool
    latency_ms: int
    success: bool
    degraded: bool
    # Integrity labels
    has_evidence_label: bool = False
    has_policy_label: bool   = False
    has_inference_label: bool = False
    has_disclaimer: bool     = False
    mcp_summary_available: bool = False
    rag_policy_available: bool  = False


# ── Simple explain endpoint ───────────────────────────────────────────────────

@router.post("", response_model=ExplainResponse)
async def explain_session(
    req: ExplainRequest,
    _: dict = Depends(require_role("teacher")),
) -> ExplainResponse:
    """
    Generate an AI explanation. Caller supplies pre-fetched MCP + RAG context.
    Uses Groq PRIMARY; falls back to NVIDIA automatically.
    Never returns a verdict — teacher makes the determination.
    """
    prompt_obj = build_incident_prompt(
        session_id=req.session_id,
        exam_title=req.exam_title,
        risk_score=req.risk_score,
        risk_level=req.risk_level,
        events=req.events,
        incident_summary=req.incident_summary or "",
        policy_context=req.policy_context or "",
        ai_detection_signals=req.ai_detection_signals,
        correlation_timeline=req.correlation_timeline,
    )
    prompt_text = prompt_obj.build()

    try:
        ai_result: AIGatewayResponse = await gateway.complete(
            prompt=prompt_text,
            max_tokens=1024,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("explain_endpoint_error", session_id=req.session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI explanation service temporarily unavailable.",
        ) from exc

    explanation = ai_result.text or (
        "AI explanation unavailable. "
        "Please review the behavioral evidence timeline directly. "
        "The deterministic risk score remains accurate."
    )

    # Ensure disclaimer is present
    disclaimer = "The final determination belongs to the reviewing teacher."
    if disclaimer.lower() not in explanation.lower():
        explanation = explanation.rstrip() + f"\n\n{disclaimer}"

    logger.info(
        "explanation_generated",
        session_id=req.session_id,
        provider=ai_result.provider,
        is_fallback=ai_result.is_fallback,
        success=ai_result.success,
        latency_ms=ai_result.latency_ms,
    )

    text_lower = explanation.lower()
    return ExplainResponse(
        session_id=req.session_id,
        explanation=explanation,
        teacher_disclaimer=disclaimer,
        provider=ai_result.provider,
        is_fallback=ai_result.is_fallback,
        latency_ms=ai_result.latency_ms,
        success=ai_result.success,
        degraded=not ai_result.success,
        has_evidence_label=LABEL_EVIDENCE.lower() in text_lower,
        has_policy_label=LABEL_POLICY.lower() in text_lower,
        has_inference_label=LABEL_INFERENCE.lower() in text_lower,
        has_disclaimer=disclaimer.lower() in text_lower,
        mcp_summary_available=bool(req.incident_summary),
        rag_policy_available=bool(req.policy_context),
    )


# ── Full orchestration endpoint ───────────────────────────────────────────────

@router.post("/full", response_model=ExplainResponse)
async def explain_session_full(
    req: FullExplainRequest,
    _: dict = Depends(require_role("teacher")),
) -> ExplainResponse:
    """
    Fully orchestrated explanation:
      1. Calls MCP create_incident_summary automatically
      2. Calls RAG get_policy_context automatically
      3. Sends structured prompt to Groq (or NVIDIA fallback)
      4. Validates output — no forbidden phrases, disclaimer present
    """
    from app.services import mcp_client, rag_client  # lazy import to avoid circular

    orchestrator = ExplanationOrchestrator(
        gateway=None,   # uses global lazy singleton
        mcp_client=mcp_client,
        rag_client=rag_client,
    )

    result: ExplanationResult = await orchestrator.explain(
        session_id=req.session_id,
        events=req.events,
        risk_score=req.risk_score,
        risk_level=req.risk_level,
        exam_title=req.exam_title,
        exam_id=req.exam_id,
        institution=req.institution,
        student_id=req.student_id,
        ai_detection_signals=req.ai_detection_signals,
        correlation_timeline=req.correlation_timeline,
    )

    logger.info(
        "full_explanation_generated",
        session_id=req.session_id,
        provider=result.provider,
        success=result.success,
        has_disclaimer=result.has_disclaimer,
        forbidden_phrase_detected=result.forbidden_phrase_detected,
        latency_ms=result.latency_ms,
    )

    return ExplainResponse(
        session_id=result.session_id,
        explanation=result.explanation,
        teacher_disclaimer=result.teacher_disclaimer,
        provider=result.provider,
        is_fallback=result.is_fallback,
        latency_ms=result.latency_ms,
        success=result.success,
        degraded=result.degraded,
        has_evidence_label=result.has_evidence_label,
        has_policy_label=result.has_policy_label,
        has_inference_label=result.has_inference_label,
        has_disclaimer=result.has_disclaimer,
        mcp_summary_available=result.mcp_summary_available,
        rag_policy_available=result.rag_policy_available,
    )


# ── Provider health ───────────────────────────────────────────────────────────

@router.get("/provider-health", tags=["Explanation"])
async def provider_health(
    _: dict = Depends(require_role("teacher")),
) -> dict[str, Any]:
    """Return current AI provider health status (teacher-only)."""
    return await gateway.health_status()
