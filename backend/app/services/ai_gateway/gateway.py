"""
AI Gateway orchestrator — Groq PRIMARY / NVIDIA FALLBACK

Responsibilities:
  1. Try Groq first (PRIMARY).
  2. On any failure trigger (timeout, 429, 5xx, quota, token limit, empty, connection),
     automatically switch to NVIDIA (FALLBACK) for that request.
  3. Track provider health; restore Groq automatically when it recovers.
  4. Log every provider request: provider, request_id, failure_reason, http_status,
     latency, fallback_activation, timestamp.
  5. When BOTH providers fail: return a structured degraded response.
     The deterministic Rules Engine remains functional regardless.

SECURITY RULES (enforced here):
  - API keys are inside ProviderClient._api_key — never exposed in any response.
  - AIGatewayResponse.content is the only field returned to callers.
  - No key appears in logs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from .config import GatewayConfig, load_gateway_config
from .health import ProviderHealth, HealthState
from .providers import (
    FallbackReason,
    ProviderCallResult,
    ProviderClient,
    make_groq_client,
    make_nvidia_client,
)

logger = structlog.get_logger(__name__)

# Failure reasons that trigger immediate fallback (no retry on same provider)
_IMMEDIATE_FALLBACK_REASONS = {
    FallbackReason.HTTP_429,
    FallbackReason.HTTP_5XX,
    FallbackReason.TIMEOUT,
    FallbackReason.CONNECTION_ERROR,
    FallbackReason.QUOTA_EXHAUSTED,
    FallbackReason.TOKEN_LIMIT,
    FallbackReason.INVALID_RESPONSE,
    FallbackReason.EMPTY_RESPONSE,
    FallbackReason.PROVIDER_UNAVAILABLE,
    FallbackReason.UNKNOWN,
}


class ProviderStatus(str, Enum):
    GROQ_PRIMARY   = "groq_primary"
    NVIDIA_FALLBACK = "nvidia_fallback"
    DEGRADED       = "degraded"          # both providers unavailable


@dataclass
class AIGatewayResponse:
    success: bool
    provider: str                          # "groq" | "nvidia" | "none"
    provider_status: ProviderStatus
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    is_fallback: bool = False
    failure_reason: str | None = None
    degraded_message: str = ""

    @property
    def text(self) -> str:
        """Convenience accessor — returns content or degraded message."""
        return self.content if self.success else self.degraded_message


# ── Gateway ───────────────────────────────────────────────────────────────────

class AIGateway:
    """
    Single entry-point for all AI completions in the platform.

    Usage:
        result = await gateway.complete(prompt="Explain this incident...")
        if result.success:
            explanation = result.content
        else:
            explanation = result.degraded_message

    The caller should never need to know which provider was used.
    """

    def __init__(self, config: GatewayConfig | None = None) -> None:
        self._config = config or load_gateway_config()
        self._groq_health  = ProviderHealth("groq",  recovery_threshold=self._config.recovery_threshold)
        self._nvidia_health = ProviderHealth("nvidia", recovery_threshold=self._config.recovery_threshold)
        self._groq  = make_groq_client(self._config)
        self._nvidia = make_nvidia_client(self._config)

    # ── Public API ────────────────────────────────────────────────────────────

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        request_id: str | None = None,
    ) -> AIGatewayResponse:
        """
        Submit a completion request. Groq is tried first; NVIDIA is the automatic
        fallback. Fallback is activated immediately on any failure trigger.
        """
        req_id = request_id or str(uuid.uuid4())
        messages = _build_messages(prompt, system_prompt)

        # ── Attempt PRIMARY (Groq) ─────────────────────────────────────────
        if self._groq_health.is_available:
            result = await self._groq.complete(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                request_id=req_id,
            )
            await self._handle_health(result, self._groq_health)
            self._log_attempt(result, is_fallback=False)

            if result.success:
                return _to_response(result, ProviderStatus.GROQ_PRIMARY, is_fallback=False)

            # Groq failed — activate fallback immediately
            logger.info(
                "groq_fallback_activated",
                request_id=req_id,
                reason=result.failure_reason.value if result.failure_reason else "unknown",
            )
        else:
            logger.info("groq_circuit_open_using_nvidia", request_id=req_id)

        # ── Attempt FALLBACK (NVIDIA) ──────────────────────────────────────
        if self._nvidia_health.is_available:
            result = await self._nvidia.complete(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                request_id=req_id,
            )
            await self._handle_health(result, self._nvidia_health)
            self._log_attempt(result, is_fallback=True)

            if result.success:
                return _to_response(result, ProviderStatus.NVIDIA_FALLBACK, is_fallback=True)

        # ── Both providers failed — degraded response ──────────────────────
        logger.error(
            "both_providers_failed_degraded_response",
            request_id=req_id,
        )
        return AIGatewayResponse(
            success=False,
            provider="none",
            provider_status=ProviderStatus.DEGRADED,
            request_id=req_id,
            is_fallback=True,
            failure_reason="both_providers_unavailable",
            degraded_message=(
                "AI explanation temporarily unavailable. "
                "The deterministic risk score and evidence timeline remain accurate. "
                "Please review the behavioral evidence directly."
            ),
        )

    async def health_status(self) -> dict[str, Any]:
        """Return current health state of both providers."""
        return {
            "groq":  self._groq_health.to_dict(),
            "nvidia": self._nvidia_health.to_dict(),
            "active_primary": (
                "groq" if self._groq_health.is_available else "nvidia"
            ),
        }

    def reset_health(self) -> None:
        """Reset all provider health — used in tests."""
        self._groq_health.reset()
        self._nvidia_health.reset()

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _handle_health(
        self, result: ProviderCallResult, tracker: ProviderHealth
    ) -> None:
        if result.success:
            await tracker.record_success()
        else:
            await tracker.record_failure()

    def _log_attempt(self, result: ProviderCallResult, is_fallback: bool) -> None:
        logger.info(
            "ai_gateway_attempt",
            provider=result.provider,
            request_id=result.request_id,
            success=result.success,
            is_fallback=is_fallback,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            failure_reason=result.failure_reason.value if result.failure_reason else None,
            fallback_activated=(not result.success and not is_fallback),
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_messages(
    prompt: str, system_prompt: str | None
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    sp = system_prompt or _DEFAULT_SYSTEM_PROMPT
    messages.append({"role": "system", "content": sp})
    messages.append({"role": "user",   "content": prompt})
    return messages


def _to_response(
    result: ProviderCallResult,
    status: ProviderStatus,
    is_fallback: bool,
) -> AIGatewayResponse:
    return AIGatewayResponse(
        success=True,
        provider=result.provider,
        provider_status=status,
        request_id=result.request_id,
        content=result.content,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        is_fallback=is_fallback,
    )


_DEFAULT_SYSTEM_PROMPT = """\
You are an AI assistant for AI Exam Guardian, an exam integrity review platform.

Your role is to EXPLAIN behavioral evidence to a human teacher reviewer.

IMPORTANT RULES:
1. Never state that a student "cheated" or is "guilty".
2. Never make a determination — the teacher makes all determinations.
3. Clearly distinguish OBSERVED EVIDENCE from POLICY INTERPRETATION from AI INFERENCE.
4. Only reference the policy text provided to you — never invent policy.
5. Be concise, factual, and professional.
6. If evidence is weak or ambiguous, say so explicitly.
7. Always end with: "The final determination belongs to the reviewing teacher."
"""
