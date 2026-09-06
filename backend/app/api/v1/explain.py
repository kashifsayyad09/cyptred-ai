"""
Explanation API — POST /api/v1/explain

Combines:
  1. MCP incident summary (evidence + risk score)
  2. RAG policy context (retrieved — never invented)
  3. AI Gateway (Groq PRIMARY / NVIDIA FALLBACK) → explanation text

The endpoint is teacher-only (role = "teacher").
Students never receive AI-generated explanations directly.

SECURITY:
  - AI keys never appear in any response.
  - policy_context is labelled as RETRIEVED — not AI-generated.
  - AI explanation always ends with teacher-determination disclaimer.
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import require_role
from app.services.ai_gateway import gateway, AIGatewayResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/explain", tags=["Explanation"])


# ── Request / Response schemas ────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    session_id: str
    student_id: Optional[str] = None
    exam_title: str = "Examination"
    risk_score: int
    risk_level: str
    events: list[dict[str, Any]] = []
    policy_context: Optional[str] = None   # pre-fetched from RAG (recommended)
    incident_summary: Optional[str] = None # pre-built by MCP (recommended)


class ExplainResponse(BaseModel):
    session_id: str
    explanation: str
    provider: str
    is_fallback: bool
    latency_ms: int
    success: bool
    degraded: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(req: ExplainRequest) -> str:
    parts: list[str] = []

    if req.incident_summary:
        parts.append("=== INCIDENT SUMMARY (from MCP Rules Engine) ===")
        parts.append(req.incident_summary)
        parts.append("")

    parts.append(f"=== SESSION DETAILS ===")
    parts.append(f"Session ID:  {req.session_id}")
    parts.append(f"Exam:        {req.exam_title}")
    parts.append(f"Risk Score:  {req.risk_score}/100")
    parts.append(f"Risk Level:  {req.risk_level}")
    parts.append(f"Event Count: {len(req.events)}")
    parts.append("")

    if req.events:
        parts.append("=== EVENT TIMELINE (OBSERVED EVIDENCE) ===")
        for ev in req.events[:25]:  # cap at 25 to avoid token exhaustion
            ts  = ev.get("timestamp", "")
            typ = ev.get("event_type", ev.get("type", "UNKNOWN"))
            parts.append(f"  {ts}  {typ}")
        if len(req.events) > 25:
            parts.append(f"  ... and {len(req.events) - 25} more events")
        parts.append("")

    if req.policy_context:
        parts.append(req.policy_context)
        parts.append("")

    parts.append(
        "Please provide a concise, factual explanation of this session's evidence "
        "for the teacher reviewer. Distinguish clearly between OBSERVED EVIDENCE, "
        "POLICY INTERPRETATION, and AI INFERENCE. Do not make a determination of guilt."
    )

    return "\n".join(parts)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ExplainResponse)
async def explain_session(
    req: ExplainRequest,
    _: dict = Depends(require_role("teacher")),
) -> ExplainResponse:
    """
    Generate an AI explanation of a session's behavioral evidence.

    - Requires teacher role.
    - Uses Groq PRIMARY; falls back to NVIDIA automatically.
    - On both-provider failure, returns a graceful degraded response.
    - Never returns an accusation or verdict.
    """
    prompt = _build_prompt(req)

    try:
        result: AIGatewayResponse = await gateway.complete(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("explain_endpoint_error", session_id=req.session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI explanation service temporarily unavailable.",
        ) from exc

    explanation = result.text  # content if success, degraded_message if not
    if not explanation:
        explanation = (
            "AI explanation unavailable. "
            "Please review the behavioral evidence timeline directly. "
            "The deterministic risk score remains accurate."
        )

    logger.info(
        "explanation_generated",
        session_id=req.session_id,
        provider=result.provider,
        is_fallback=result.is_fallback,
        success=result.success,
        latency_ms=result.latency_ms,
    )

    return ExplainResponse(
        session_id=req.session_id,
        explanation=explanation,
        provider=result.provider,
        is_fallback=result.is_fallback,
        latency_ms=result.latency_ms,
        success=result.success,
        degraded=not result.success,
    )


@router.get("/provider-health", tags=["Explanation"])
async def provider_health(
    _: dict = Depends(require_role("teacher")),
) -> dict[str, Any]:
    """Return current AI provider health status (teacher-only)."""
    return await gateway.health_status()
