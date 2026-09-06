"""
AI Gateway — Groq PRIMARY / NVIDIA FALLBACK

Public API:
    from app.services.ai_gateway import AIGateway, AIGatewayResponse, ProviderStatus

    result = await AIGateway().complete(prompt="...")
    if result.success:
        print(result.content)
    else:
        print(result.degraded_message)

The module-level `gateway` singleton is created lazily via get_gateway()
so that importing this module in test environments (without pydantic_settings)
does not immediately fail.
"""

from .gateway import AIGateway, AIGatewayResponse, ProviderStatus, FallbackReason
from .health import ProviderHealth, HealthState

# Lazy singleton — call get_gateway() instead of importing `gateway` directly
# in test environments where pydantic_settings may not be available.
_gateway_instance: "AIGateway | None" = None


def get_gateway() -> "AIGateway":
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = AIGateway()
    return _gateway_instance


# Convenience alias for production code that imports `gateway` directly.
# Accessing this attribute at module level is safe because Python does not
# evaluate it until the attribute is actually read.
class _LazyGateway:
    """Proxy that creates the real gateway on first attribute access."""
    def __getattr__(self, name):
        return getattr(get_gateway(), name)

    async def complete(self, *args, **kwargs):
        return await get_gateway().complete(*args, **kwargs)

    async def health_status(self, *args, **kwargs):
        return await get_gateway().health_status(*args, **kwargs)

    def reset_health(self):
        get_gateway().reset_health()


gateway = _LazyGateway()

__all__ = [
    "gateway",
    "get_gateway",
    "AIGateway",
    "AIGatewayResponse",
    "ProviderStatus",
    "FallbackReason",
    "ProviderHealth",
    "HealthState",
]
