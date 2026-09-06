"""
AI Assistant Detector — core detection logic.

Combines multiple signals into a final detection verdict:

  DETECTED     — Observable signals strongly associated with AI assistant use
  SUSPECTED    — Behavioral patterns consistent with AI assistant use;
                 insufficient for certainty
  NOT_DETECTED — No observable signals detected in this session
  UNOBSERVABLE — The activity cannot be observed by available browser APIs

IMPORTANT:
  - No single signal is conclusive.
  - Absence of DETECTED does NOT prove the software was not used.
  - ParakeetAI is specifically designed to evade standard detection.
  - The final decision always belongs to the teacher/institution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mcp.detectors.ai_assistant_detector.registry import (
    find_by_domain, REGISTRY, AssistantEntry,
)
from mcp.detectors.ai_assistant_detector.signals import (
    SignalResult,
    signal_domain_navigation,
    signal_focus_copy_paste_sequence,
    signal_rapid_large_paste,
    signal_repeated_navigation,
    signal_keyboard_pattern,
)


# ── Detection state ───────────────────────────────────────────────────────────

class DetectionState(str, Enum):
    DETECTED     = "DETECTED"
    SUSPECTED    = "SUSPECTED"
    NOT_DETECTED = "NOT_DETECTED"
    UNOBSERVABLE = "UNOBSERVABLE"


# ── Detection result ──────────────────────────────────────────────────────────

@dataclass
class AssistantDetectionResult:
    """Result for a single AI assistant target."""
    assistant_name: str
    primary_domain: str
    detection_state: DetectionState
    confidence: float          # 0.0–1.0
    signals_triggered: list[SignalResult]
    evidence_summary: str


@dataclass
class DetectionReport:
    """Full detection report for a session."""
    session_id: str
    overall_state: DetectionState
    overall_confidence: float
    per_assistant: list[AssistantDetectionResult]
    all_signals: list[SignalResult]
    additional_score: int      # bonus score to add to risk engine
    summary: str
    limitation_notice: str = (
        "This report reflects observable browser signals only. "
        "No browser-based system can detect all AI assistant usage with certainty. "
        "ParakeetAI and similar tools are specifically designed to evade detection. "
        "Absence of DETECTED does not prove the software was not used. "
        "The final determination belongs to the teacher or institution."
    )


# ── Detector ──────────────────────────────────────────────────────────────────

class AIAssistantDetector:
    """
    Runs all signal extractors over a session's event list and produces
    a structured DetectionReport.

    Detection priority:
      1. ParakeetAI (primary target — highest evasion risk)
      2. ChatGPT, Claude, Gemini, Copilot, Perplexity
    """

    # Thresholds for state classification
    DETECTED_THRESHOLD  = 0.80   # domain signal → confident DETECTED
    SUSPECTED_THRESHOLD = 0.45   # behavioral signal → SUSPECTED

    def detect(
        self,
        events: list[dict[str, Any]],
        session_id: str = "",
    ) -> DetectionReport:
        """Run all detectors over the event list and return a full report."""

        # 1. Run all signal extractors
        all_signals: list[SignalResult] = []
        all_signals.extend(signal_domain_navigation(events))
        all_signals.extend(signal_focus_copy_paste_sequence(events))
        all_signals.extend(signal_rapid_large_paste(events))
        all_signals.extend(signal_repeated_navigation(events))
        all_signals.extend(signal_keyboard_pattern(events))

        # 2. Per-assistant results
        per_assistant = self._evaluate_per_assistant(all_signals, events)

        # 3. Overall state
        overall_state, overall_conf = self._aggregate_state(per_assistant, all_signals)

        # 4. Additional risk score contribution
        additional_score = self._compute_additional_score(overall_state, overall_conf)

        # 5. Summary
        summary = self._build_summary(overall_state, per_assistant, all_signals)

        return DetectionReport(
            session_id=session_id,
            overall_state=overall_state,
            overall_confidence=overall_conf,
            per_assistant=per_assistant,
            all_signals=all_signals,
            additional_score=additional_score,
            summary=summary,
        )

    # ── Per-assistant evaluation ──────────────────────────────────────────────

    def _evaluate_per_assistant(
        self,
        signals: list[SignalResult],
        events: list[dict],
    ) -> list[AssistantDetectionResult]:
        results = []
        for entry in REGISTRY:
            relevant = [
                s for s in signals
                if s.assistant == entry.name or s.domain in (
                    (entry.primary_domain,) + entry.aliases
                )
            ]
            state, confidence = self._classify_assistant(relevant, entry)
            results.append(AssistantDetectionResult(
                assistant_name=entry.name,
                primary_domain=entry.primary_domain,
                detection_state=state,
                confidence=confidence,
                signals_triggered=relevant,
                evidence_summary=self._assistant_summary(entry.name, state, relevant),
            ))
        return results

    def _classify_assistant(
        self,
        signals: list[SignalResult],
        entry: AssistantEntry,
    ) -> tuple[DetectionState, float]:
        if not signals:
            # No signals at all — may be UNOBSERVABLE for high-evasion tools
            if entry.evasion_risk == "critical":
                return DetectionState.UNOBSERVABLE, 0.0
            return DetectionState.NOT_DETECTED, 0.0

        # Domain navigation signal → strongest evidence
        domain_signals = [s for s in signals if s.signal_name == "domain_navigation"]
        if domain_signals:
            max_conf = max(s.confidence for s in domain_signals)
            if max_conf >= self.DETECTED_THRESHOLD:
                return DetectionState.DETECTED, max_conf
            return DetectionState.SUSPECTED, max_conf

        # Behavioral signals only → SUSPECTED
        max_conf = max(s.confidence for s in signals)
        if max_conf >= self.SUSPECTED_THRESHOLD:
            return DetectionState.SUSPECTED, max_conf

        return DetectionState.NOT_DETECTED, max_conf

    # ── Overall state aggregation ─────────────────────────────────────────────

    def _aggregate_state(
        self,
        per_assistant: list[AssistantDetectionResult],
        all_signals: list[SignalResult],
    ) -> tuple[DetectionState, float]:
        # If any assistant is DETECTED → overall DETECTED
        detected = [r for r in per_assistant if r.detection_state == DetectionState.DETECTED]
        if detected:
            return DetectionState.DETECTED, max(r.confidence for r in detected)

        # If any is SUSPECTED → overall SUSPECTED
        suspected = [r for r in per_assistant if r.detection_state == DetectionState.SUSPECTED]
        if suspected:
            return DetectionState.SUSPECTED, max(r.confidence for r in suspected)

        # If all signals triggered but no domain match → SUSPECTED (behavioral only)
        behavioral = [
            s for s in all_signals
            if s.signal_name in ("focus_copy_paste_sequence", "rapid_large_paste", "repeated_navigation")
            and s.triggered
        ]
        if behavioral:
            return DetectionState.SUSPECTED, max(s.confidence for s in behavioral)

        # If any high-evasion assistant is UNOBSERVABLE and no positive signals → UNOBSERVABLE
        any_unobservable = any(
            r.detection_state == DetectionState.UNOBSERVABLE for r in per_assistant
        )
        if any_unobservable and not behavioral:
            return DetectionState.UNOBSERVABLE, 0.0

        return DetectionState.NOT_DETECTED, 0.0

    # ── Score contribution ────────────────────────────────────────────────────

    def _compute_additional_score(
        self, state: DetectionState, confidence: float
    ) -> int:
        if state == DetectionState.DETECTED:
            return 25
        if state == DetectionState.SUSPECTED:
            return int(25 * confidence)
        return 0

    # ── Summaries ─────────────────────────────────────────────────────────────

    def _build_summary(
        self,
        state: DetectionState,
        per_assistant: list[AssistantDetectionResult],
        signals: list[SignalResult],
    ) -> str:
        triggered = [s for s in signals if s.triggered]
        if state == DetectionState.DETECTED:
            names = [r.assistant_name for r in per_assistant if r.detection_state == DetectionState.DETECTED]
            return (
                f"AI assistant signal DETECTED for: {', '.join(names)}. "
                f"{len(triggered)} signal(s) triggered. Teacher review recommended."
            )
        if state == DetectionState.SUSPECTED:
            return (
                f"AI assistant usage SUSPECTED based on behavioral patterns. "
                f"{len(triggered)} signal(s) triggered. "
                "No specific tool identified with certainty."
            )
        if state == DetectionState.UNOBSERVABLE:
            return (
                "AI assistant activity cannot be confirmed or ruled out — "
                "observable signals are insufficient. "
                "Tools like ParakeetAI are specifically designed to avoid detection."
            )
        return "No AI assistant signals detected in this session."

    def _assistant_summary(
        self,
        name: str,
        state: DetectionState,
        signals: list[SignalResult],
    ) -> str:
        if not signals:
            return f"{name}: No signals detected."
        descs = "; ".join(s.description for s in signals[:3])
        return f"{name} [{state.value}]: {descs}"
