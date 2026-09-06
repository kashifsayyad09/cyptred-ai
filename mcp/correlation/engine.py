"""
Evidence Correlation Engine.

Single events have limited significance.
This engine sequences events into meaningful chains and produces
a structured evidence timeline and correlated findings.

Example high-signal sequence:
  AI domain navigation → return to exam → copy → paste → rapid answer change
  → produces stronger evidence than any single event alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.rules.rules_engine import EventType


# ── Timeline entry ────────────────────────────────────────────────────────────

@dataclass
class TimelineEntry:
    timestamp: str           # ISO-8601
    event_type: str
    source: str
    rule: str | None
    severity: str            # low | medium | high | critical
    score_contribution: int
    confidence: float        # 0.0–1.0
    metadata: dict[str, Any]
    description: str


# ── Sequence patterns ─────────────────────────────────────────────────────────

@dataclass
class CorrelatedSequence:
    name: str
    events: list[str]        # event types in order
    extra_weight: int        # bonus weight on top of individual scores
    confidence: float
    description: str


# High-signal sequences the engine watches for
KNOWN_SEQUENCES: list[CorrelatedSequence] = [
    CorrelatedSequence(
        name="ai_navigation_paste",
        events=[EventType.AI_ASSISTANT_SIGNAL, EventType.PASTE],
        extra_weight=20,
        confidence=0.85,
        description=(
            "AI assistant domain signal followed by paste — "
            "strongly consistent with AI-assisted answer insertion."
        ),
    ),
    CorrelatedSequence(
        name="focus_loss_navigation_paste",
        events=[EventType.FOCUS_LOSS, EventType.SUSPICIOUS_NAVIGATION, EventType.PASTE],
        extra_weight=20,
        confidence=0.75,
        description=(
            "Focus loss → external navigation → paste sequence — "
            "consistent with consulting an external resource and copying the result."
        ),
    ),
    CorrelatedSequence(
        name="tab_switch_copy_paste",
        events=[EventType.TAB_SWITCH, EventType.COPY, EventType.PASTE],
        extra_weight=15,
        confidence=0.65,
        description=(
            "Tab switch followed by copy then paste — "
            "possible transfer from another tab."
        ),
    ),
    CorrelatedSequence(
        name="devtools_navigation",
        events=[EventType.DEVTOOLS_SHORTCUT, EventType.SUSPICIOUS_NAVIGATION],
        extra_weight=10,
        confidence=0.60,
        description="DevTools shortcut combined with suspicious navigation.",
    ),
]


# ── Correlation Engine ────────────────────────────────────────────────────────

@dataclass
class CorrelationResult:
    timeline: list[TimelineEntry]
    matched_sequences: list[CorrelatedSequence]
    sequence_bonus: int
    summary: str


class CorrelationEngine:
    """
    Analyses a list of raw events, builds a timeline, and detects known
    high-signal sequences that warrant additional review weight.
    """

    # Max time window in which a sequence must occur (seconds)
    SEQUENCE_WINDOW_S: int = 300

    def correlate(self, events: list[dict[str, Any]]) -> CorrelationResult:
        timeline = self._build_timeline(events)
        matched, bonus = self._detect_sequences(events)
        summary = self._build_summary(timeline, matched)
        return CorrelationResult(
            timeline=timeline,
            matched_sequences=matched,
            sequence_bonus=bonus,
            summary=summary,
        )

    # ── Timeline ─────────────────────────────────────────────────────────────

    def _build_timeline(self, events: list[dict]) -> list[TimelineEntry]:
        entries = []
        for ev in events:
            etype = ev.get("event_type", "UNKNOWN")
            entries.append(TimelineEntry(
                timestamp=ev.get("occurred_at", ""),
                event_type=etype,
                source=ev.get("source", "extension"),
                rule=self._rule_for(etype),
                severity=self._severity_for(etype),
                score_contribution=self._base_weight_for(etype),
                confidence=self._confidence_for(etype),
                metadata=ev.get("metadata") or {},
                description=self._describe(etype, ev.get("metadata") or {}),
            ))
        # Sort chronologically
        entries.sort(key=lambda e: e.timestamp)
        return entries

    # ── Sequence detection ────────────────────────────────────────────────────

    def _detect_sequences(
        self, events: list[dict]
    ) -> tuple[list[CorrelatedSequence], int]:
        """
        Check each known sequence pattern against the event list.
        Returns matched sequences and total bonus weight.
        """
        matched = []
        bonus = 0

        event_types = [e.get("event_type", "") for e in events]
        timestamps = [e.get("occurred_at", "") for e in events]

        for seq in KNOWN_SEQUENCES:
            if self._sequence_present(seq.events, event_types, timestamps):
                matched.append(seq)
                bonus += seq.extra_weight

        return matched, min(bonus, 40)  # cap sequence bonus

    def _sequence_present(
        self,
        pattern: list[str],
        event_types: list[str],
        timestamps: list[str],
    ) -> bool:
        """
        Check if the pattern events appear in order within the time window.
        Uses a greedy forward scan.
        """
        pos = 0
        last_ts: datetime | None = None

        for step in pattern:
            found = False
            while pos < len(event_types):
                if event_types[pos] == step:
                    ts = self._parse_ts(timestamps[pos])
                    if last_ts is None or (
                        ts is not None and
                        ts - last_ts <= timedelta(seconds=self.SEQUENCE_WINDOW_S)
                    ):
                        last_ts = ts
                        pos += 1
                        found = True
                        break
                pos += 1
            if not found:
                return False
        return True

    # ── Summary ───────────────────────────────────────────────────────────────

    def _build_summary(
        self, timeline: list[TimelineEntry], matched: list[CorrelatedSequence]
    ) -> str:
        if not timeline:
            return "No events recorded for this session."

        event_count = len(timeline)
        high_critical = [e for e in timeline if e.severity in ("high", "critical")]
        parts = [f"Session contains {event_count} recorded event(s)."]

        if high_critical:
            parts.append(
                f"{len(high_critical)} high/critical severity event(s) detected."
            )
        if matched:
            for seq in matched:
                parts.append(f"Sequence detected: {seq.description}")

        parts.append(
            "Evidence does not by itself establish intentional policy violation — "
            "teacher review recommended."
        )
        return " ".join(parts)

    # ── Helpers ───────────────────────────────────────────────────────────────

    _SEVERITY_MAP = {
        EventType.AI_ASSISTANT_SIGNAL:   "critical",
        EventType.SUSPICIOUS_NAVIGATION: "high",
        EventType.COPY:                  "medium",
        EventType.PASTE:                 "medium",
        EventType.TAB_SWITCH:            "medium",
        EventType.FOCUS_LOSS:            "low",
        EventType.WINDOW_BLUR:           "low",
        EventType.FULLSCREEN_EXIT:       "medium",
        EventType.DEVTOOLS_SHORTCUT:     "high",
        EventType.KEYBOARD_SHORTCUT:     "low",
    }

    _BASE_WEIGHTS = {
        EventType.TAB_SWITCH: 10, EventType.TAB_HIDDEN: 10,
        EventType.FOCUS_LOSS: 5,  EventType.WINDOW_BLUR: 5,
        EventType.COPY: 15,       EventType.PASTE: 15,
        EventType.FULLSCREEN_EXIT: 10,
        EventType.SUSPICIOUS_NAVIGATION: 20,
        EventType.AI_ASSISTANT_SIGNAL: 25,
        EventType.DEVTOOLS_SHORTCUT: 20,
    }

    _RULE_MAP = {
        EventType.AI_ASSISTANT_SIGNAL:   "check_ai_assistant_signal",
        EventType.TAB_SWITCH:            "check_tab_switch",
        EventType.TAB_HIDDEN:            "check_tab_switch",
        EventType.FOCUS_LOSS:            "check_focus_loss",
        EventType.WINDOW_BLUR:           "check_focus_loss",
        EventType.COPY:                  "check_copy",
        EventType.PASTE:                 "check_paste",
        EventType.FULLSCREEN_EXIT:       "check_fullscreen",
        EventType.SUSPICIOUS_NAVIGATION: "check_navigation",
        EventType.DEVTOOLS_SHORTCUT:     "check_devtools_signal",
        EventType.KEYBOARD_SHORTCUT:     "check_keyboard_shortcuts",
    }

    def _severity_for(self, etype: str) -> str:
        return self._SEVERITY_MAP.get(etype, "low")

    def _base_weight_for(self, etype: str) -> int:
        return self._BASE_WEIGHTS.get(etype, 0)

    def _rule_for(self, etype: str) -> str | None:
        return self._RULE_MAP.get(etype)

    def _confidence_for(self, etype: str) -> float:
        HIGH = {EventType.AI_ASSISTANT_SIGNAL, EventType.DEVTOOLS_SHORTCUT}
        MED  = {EventType.PASTE, EventType.COPY, EventType.SUSPICIOUS_NAVIGATION}
        if etype in HIGH: return 0.90
        if etype in MED:  return 0.70
        return 0.50

    def _describe(self, etype: str, meta: dict) -> str:
        descriptions = {
            EventType.TAB_SWITCH:            "Student switched browser tab",
            EventType.TAB_HIDDEN:            "Exam tab hidden",
            EventType.FOCUS_LOSS:            "Exam window lost focus",
            EventType.WINDOW_BLUR:           "Exam window blurred",
            EventType.COPY:                  "Copy event during exam",
            EventType.PASTE:                 f"Paste event (length={meta.get('pasteLength', '?')})",
            EventType.FULLSCREEN_EXIT:       "Student exited fullscreen mode",
            EventType.SUSPICIOUS_NAVIGATION: f"Navigation to {meta.get('toUrl', 'unknown')}",
            EventType.AI_ASSISTANT_SIGNAL:   f"AI assistant signal: {meta.get('assistant_name', 'unknown')}",
            EventType.DEVTOOLS_SHORTCUT:     f"DevTools shortcut: {meta.get('key', '?')}",
            EventType.KEYBOARD_SHORTCUT:     f"Keyboard shortcut: {meta.get('combo', '?')}",
        }
        return descriptions.get(etype, f"Event: {etype}")

    @staticmethod
    def _parse_ts(ts_str: str) -> datetime | None:
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return None
