"""
AI Assistant Domain Registry.

Single source of truth for all monitored AI assistant domains.
ParakeetAI is the PRIMARY TARGET — it is specifically designed
to evade standard proctoring detection, requiring defense in depth.

IMPORTANT:
  Absence of a DETECTED signal does NOT prove the software was not used.
  These are observable signals only — not proof of intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssistantEntry:
    name: str
    primary_domain: str
    aliases: tuple[str, ...]
    risk_weight: int
    evasion_risk: str   # low | medium | high | critical
    notes: str


# ── Registry ──────────────────────────────────────────────────────────────────
# Ordered by priority: ParakeetAI first (primary target)

REGISTRY: list[AssistantEntry] = [
    AssistantEntry(
        name="ParakeetAI",
        primary_domain="parakeet-ai.com",
        aliases=("www.parakeet-ai.com", "app.parakeet-ai.com", "parakeet.ai"),
        risk_weight=25,
        evasion_risk="critical",
        notes=(
            "Specifically designed to operate without triggering standard screen-share "
            "or tab-switch detection. Claims invisible operation during proctored exams. "
            "Defense in depth required: domain signals alone are insufficient. "
            "Behavioral sequence correlation (navigation → copy → paste) is the "
            "primary detection method."
        ),
    ),
    AssistantEntry(
        name="ChatGPT",
        primary_domain="chat.openai.com",
        aliases=("chatgpt.com", "www.chatgpt.com", "openai.com"),
        risk_weight=25,
        evasion_risk="medium",
        notes="Primary OpenAI conversational assistant.",
    ),
    AssistantEntry(
        name="Claude",
        primary_domain="claude.ai",
        aliases=("www.claude.ai",),
        risk_weight=25,
        evasion_risk="medium",
        notes="Anthropic Claude assistant.",
    ),
    AssistantEntry(
        name="Gemini",
        primary_domain="gemini.google.com",
        aliases=("bard.google.com", "aistudio.google.com"),
        risk_weight=25,
        evasion_risk="medium",
        notes="Google Gemini / Bard assistant.",
    ),
    AssistantEntry(
        name="Microsoft Copilot",
        primary_domain="copilot.microsoft.com",
        aliases=("www.bing.com", "bing.com"),
        risk_weight=25,
        evasion_risk="medium",
        notes="Microsoft Copilot (formerly Bing Chat).",
    ),
    AssistantEntry(
        name="Perplexity",
        primary_domain="perplexity.ai",
        aliases=("www.perplexity.ai",),
        risk_weight=25,
        evasion_risk="medium",
        notes="Perplexity AI search assistant.",
    ),
]

# ── Lookup helpers ────────────────────────────────────────────────────────────

def _build_lookup() -> dict[str, AssistantEntry]:
    """Build a flat domain→entry map (primary + aliases)."""
    lookup: dict[str, AssistantEntry] = {}
    for entry in REGISTRY:
        lookup[entry.primary_domain] = entry
        for alias in entry.aliases:
            lookup[alias] = entry
    return lookup


_DOMAIN_LOOKUP: dict[str, AssistantEntry] = _build_lookup()


def get_all_domains() -> list[str]:
    """All monitored domains (primary + aliases)."""
    return list(_DOMAIN_LOOKUP.keys())


def find_by_domain(domain: str) -> AssistantEntry | None:
    """Return the AssistantEntry for a domain, or None if not monitored."""
    # Exact match first
    if domain in _DOMAIN_LOOKUP:
        return _DOMAIN_LOOKUP[domain]
    # Suffix match (e.g. sub.parakeet-ai.com → parakeet-ai.com)
    for monitored, entry in _DOMAIN_LOOKUP.items():
        if domain.endswith("." + monitored) or domain == monitored:
            return entry
    return None


def is_monitored_domain(domain: str) -> bool:
    return find_by_domain(domain) is not None
