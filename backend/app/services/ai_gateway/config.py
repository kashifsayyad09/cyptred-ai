"""
AI Gateway configuration — loaded from the backend Settings object.

All values come from environment variables via backend/app/core/config.py.
No secrets are ever hardcoded here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayConfig:
    # Groq
    groq_api_key: str
    groq_base_url: str
    groq_model: str
    groq_timeout: float
    groq_max_retries: int

    # NVIDIA
    nvidia_api_key: str
    nvidia_base_url: str
    nvidia_model: str
    nvidia_timeout: float
    nvidia_max_retries: int

    # Health / recovery
    health_check_interval: int   # seconds between health probes
    recovery_threshold: int      # consecutive successes before restoring primary


def load_gateway_config() -> GatewayConfig:
    """Build GatewayConfig from the application Settings singleton."""
    from app.core.config import settings

    return GatewayConfig(
        groq_api_key=settings.GROQ_API_KEY,
        groq_base_url=settings.GROQ_BASE_URL,
        groq_model=settings.GROQ_MODEL,
        groq_timeout=float(settings.GROQ_TIMEOUT_SECONDS),
        groq_max_retries=settings.GROQ_MAX_RETRIES,

        nvidia_api_key=settings.NVIDIA_API_KEY,
        nvidia_base_url=settings.NVIDIA_BASE_URL,
        nvidia_model=settings.NVIDIA_MODEL,
        nvidia_timeout=float(settings.NVIDIA_TIMEOUT_SECONDS),
        nvidia_max_retries=settings.NVIDIA_MAX_RETRIES,

        health_check_interval=int(
            __import__("os").environ.get("AI_GATEWAY_HEALTH_INTERVAL", "60")
        ),
        recovery_threshold=int(
            __import__("os").environ.get("AI_GATEWAY_RECOVERY_THRESHOLD", "3")
        ),
    )
