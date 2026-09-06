"""
Provider clients — thin async wrappers around the OpenAI-compatible APIs.

Both Groq and NVIDIA NIM expose an OpenAI-compatible chat completions endpoint.
We use raw httpx so we can precisely control timeouts, retries, and error handling.

IMPORTANT:
  - API keys are NEVER logged.
  - API keys are NEVER returned in any response struct.
  - Keys are only used in the Authorization header of outbound HTTP requests.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
import structlog

from .config import GatewayConfig

logger = structlog.get_logger(__name__)


# ── Failure reasons (for logging + fallback decisions) ────────────────────────

class FallbackReason(str, Enum):
    TIMEOUT            = "timeout"
    CONNECTION_ERROR   = "connection_error"
    HTTP_429           = "http_429"
    HTTP_5XX           = "http_5xx"
    QUOTA_EXHAUSTED    = "quota_exhausted"
    TOKEN_LIMIT        = "token_context_limit"
    INVALID_RESPONSE   = "invalid_response"
    EMPTY_RESPONSE     = "empty_response"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNKNOWN            = "unknown"


# ── Per-call result ───────────────────────────────────────────────────────────

@dataclass
class ProviderCallResult:
    success: bool
    provider: str                     # "groq" | "nvidia" | "none"
    request_id: str                   = field(default_factory=lambda: str(uuid.uuid4()))
    content: str                      = ""
    model: str                        = ""
    prompt_tokens: int | None         = None
    completion_tokens: int | None     = None
    latency_ms: int                   = 0
    http_status: int | None           = None
    failure_reason: FallbackReason | None = None
    error_detail: str                 = ""


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _classify_http_error(exc: httpx.HTTPStatusError) -> FallbackReason:
    code = exc.response.status_code
    if code == 429:
        return FallbackReason.HTTP_429
    if code >= 500:
        return FallbackReason.HTTP_5XX
    return FallbackReason.UNKNOWN


def _extract_content(data: dict[str, Any]) -> str:
    """Extract assistant message text from OpenAI-compatible response."""
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _extract_usage(data: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = data.get("usage") or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


# ── Provider clients ──────────────────────────────────────────────────────────

class ProviderClient:
    """
    Generic OpenAI-compatible provider client.
    Handles a single POST to /chat/completions with precise error classification.
    """

    def __init__(self, name: str, base_url: str, api_key: str,
                 model: str, timeout: float) -> None:
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key          # never logged
        self._model = model
        self._timeout = timeout

    async def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.2,
        request_id: str | None = None,
    ) -> ProviderCallResult:
        req_id = request_id or str(uuid.uuid4())
        started = time.monotonic()

        payload = {
            "model":       self._model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                latency_ms = int((time.monotonic() - started) * 1000)

                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    reason = _classify_http_error(exc)
                    logger.warning(
                        "provider_http_error",
                        provider=self._name,
                        request_id=req_id,
                        status=exc.response.status_code,
                        reason=reason.value,
                        latency_ms=latency_ms,
                    )
                    return ProviderCallResult(
                        success=False,
                        provider=self._name,
                        request_id=req_id,
                        latency_ms=latency_ms,
                        http_status=exc.response.status_code,
                        failure_reason=reason,
                        error_detail=str(exc),
                    )

                data = resp.json()
                content = _extract_content(data)
                if not content:
                    logger.warning(
                        "provider_empty_response",
                        provider=self._name,
                        request_id=req_id,
                        latency_ms=latency_ms,
                    )
                    return ProviderCallResult(
                        success=False,
                        provider=self._name,
                        request_id=req_id,
                        latency_ms=latency_ms,
                        http_status=resp.status_code,
                        failure_reason=FallbackReason.EMPTY_RESPONSE,
                        error_detail="Empty choices in response",
                    )

                prompt_tok, compl_tok = _extract_usage(data)
                logger.info(
                    "provider_success",
                    provider=self._name,
                    request_id=req_id,
                    model=self._model,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tok,
                    completion_tokens=compl_tok,
                )
                return ProviderCallResult(
                    success=True,
                    provider=self._name,
                    request_id=req_id,
                    content=content,
                    model=self._model,
                    prompt_tokens=prompt_tok,
                    completion_tokens=compl_tok,
                    latency_ms=latency_ms,
                    http_status=resp.status_code,
                )

        except httpx.TimeoutException as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "provider_timeout",
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
            )
            return ProviderCallResult(
                success=False,
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
                failure_reason=FallbackReason.TIMEOUT,
                error_detail=str(exc),
            )

        except httpx.ConnectError as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "provider_connection_error",
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
            )
            return ProviderCallResult(
                success=False,
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
                failure_reason=FallbackReason.CONNECTION_ERROR,
                error_detail=str(exc),
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.error(
                "provider_unexpected_error",
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
                error=str(exc),
            )
            return ProviderCallResult(
                success=False,
                provider=self._name,
                request_id=req_id,
                latency_ms=latency_ms,
                failure_reason=FallbackReason.UNKNOWN,
                error_detail=str(exc),
            )


def make_groq_client(cfg: GatewayConfig) -> ProviderClient:
    return ProviderClient(
        name="groq",
        base_url=cfg.groq_base_url,
        api_key=cfg.groq_api_key,
        model=cfg.groq_model,
        timeout=cfg.groq_timeout,
    )


def make_nvidia_client(cfg: GatewayConfig) -> ProviderClient:
    return ProviderClient(
        name="nvidia",
        base_url=cfg.nvidia_base_url,
        api_key=cfg.nvidia_api_key,
        model=cfg.nvidia_model,
        timeout=cfg.nvidia_timeout,
    )
