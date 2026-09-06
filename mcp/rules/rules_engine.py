"""
Behavioral Rules Engine — deterministic event scoring.

Each event type maps to a configured weight (from environment).
The engine accumulates a score and returns contributing evidence.

LLMs NEVER influence the numerical score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp.config import RiskWeights, load_weights
from mcp.rules.risk_level import RiskLevel, classify


# ── Event type constants (must match extension EVENT_TYPES) ──────────────────

class EventType:
    TAB_SWITCH           = "TAB_SWITCH"
    TAB_HIDDEN           = "TAB_HIDDEN"
    FOCUS_LOSS           = "FOCUS_LOSS"
    WINDOW_BLUR          = "WINDOW_BLUR"
    COPY                 = "COPY"
    PASTE                = "PASTE"
    FULLSCREEN_EXIT      = "FULLSCREEN_EXIT"
    NAVIGATION           = "NAVIGATION"
    SUSPICIOUS_NAVIGATION = "SUSPICIOUS_NAVIGATION"
    AI_ASSISTANT_SIGNAL  = "AI_ASSISTANT_SIGNAL"
    DEVTOOLS_SHORTCUT    = "DEVTOOLS_SHORTCUT"
    KEYBOARD_SHORTCUT    = "KEYBOARD_SHORTCUT"
    REPEATED_VIOLATION   = "REPEATED_VIOLATION"
    SUSPICIOUS_SEQUENCE  = "SUSPICIOUS_SEQUENCE"


@dataclass
class ScoredEvent:
    event_type: str
    weight: int
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    total_score: int
    risk_level: RiskLevel
    scored_events: list[ScoredEvent]
    notes: list[str]


class RulesEngine:
    """
    Applies configurable scoring weights to a list of telemetry events.
    Returns a deterministic RuleResult.
    """

    def __init__(self, weights: RiskWeights | None = None) -> None:
        self.weights = weights or load_weights()

    def evaluate(self, events: list[dict[str, Any]]) -> RuleResult:
        """
        Score a list of raw event dicts.

        Each dict must have at least:
          { "event_type": str, "occurred_at": str, "metadata": dict }
        """
        scored: list[ScoredEvent] = []
        notes: list[str] = []
        total = 0

        for event in events:
            etype = event.get("event_type", "")
            meta = event.get("metadata") or {}
            result = self._score_event(etype, meta)
            if result:
                scored.append(result)
                total += result.weight

        # Cap at 100
        total = min(total, 100)
        level = classify(total)

        # Add notes for high-signal combinations
        notes.extend(self._generate_notes(scored))

        return RuleResult(
            total_score=total,
            risk_level=level,
            scored_events=scored,
            notes=notes,
        )

    def _score_event(self, etype: str, meta: dict) -> ScoredEvent | None:
        w = self.weights
        match etype:
            case EventType.TAB_SWITCH | EventType.TAB_HIDDEN:
                return ScoredEvent(etype, w.tab_switch, "Student switched away from exam tab", meta)
            case EventType.FOCUS_LOSS | EventType.WINDOW_BLUR:
                return ScoredEvent(etype, w.focus_loss, "Exam window lost focus", meta)
            case EventType.COPY:
                return ScoredEvent(etype, w.copy, "Copy event during exam", meta)
            case EventType.PASTE:
                paste_len = meta.get("pasteLength", 0)
                reason = f"Paste event during exam (length={paste_len})"
                return ScoredEvent(etype, w.paste, reason, meta)
            case EventType.FULLSCREEN_EXIT:
                return ScoredEvent(etype, w.fullscreen_exit, "Student exited fullscreen", meta)
            case EventType.SUSPICIOUS_NAVIGATION | EventType.NAVIGATION:
                to_url = meta.get("toUrl", "")
                return ScoredEvent(etype, w.suspicious_navigation, f"Navigation signal: {to_url}", meta)
            case EventType.AI_ASSISTANT_SIGNAL:
                name = meta.get("assistant_name", "unknown")
                domain = meta.get("domain", "")
                state = meta.get("detection_state", "SUSPECTED")
                return ScoredEvent(
                    etype, w.ai_assistant_signal,
                    f"AI assistant signal: {name} ({domain}) — {state}", meta
                )
            case EventType.DEVTOOLS_SHORTCUT:
                key = meta.get("key", "")
                return ScoredEvent(etype, w.suspicious_navigation, f"DevTools shortcut: {key}", meta)
            case EventType.REPEATED_VIOLATION:
                return ScoredEvent(etype, w.repeated_violations, "Repeated policy violation", meta)
            case EventType.SUSPICIOUS_SEQUENCE:
                return ScoredEvent(etype, w.suspicious_sequence, "Suspicious behavioral sequence detected", meta)
            case _:
                return None  # Unknown event — not scored

    def _generate_notes(self, scored: list[ScoredEvent]) -> list[str]:
        notes = []
        types = {s.event_type for s in scored}

        # Navigation → paste sequence (high-signal)
        nav_types = {EventType.SUSPICIOUS_NAVIGATION, EventType.NAVIGATION, EventType.AI_ASSISTANT_SIGNAL}
        if nav_types & types and EventType.PASTE in types:
            notes.append(
                "Navigation followed by paste detected — "
                "consistent with external resource consultation."
            )

        # AI signal + copy/paste
        if EventType.AI_ASSISTANT_SIGNAL in types and (
            EventType.COPY in types or EventType.PASTE in types
        ):
            notes.append(
                "AI assistant signal combined with copy/paste activity — "
                "warrants teacher review under configured exam policy."
            )

        # Multiple focus losses
        focus_count = sum(1 for s in scored if s.event_type in {EventType.FOCUS_LOSS, EventType.WINDOW_BLUR})
        if focus_count >= 3:
            notes.append(f"Focus lost {focus_count} times — student repeatedly left the exam window.")

        return notes
