"""
Prompt builder for AI incident explanations.

Builds a structured prompt that forces the AI to:
  1. Label OBSERVED EVIDENCE vs POLICY INTERPRETATION vs AI INFERENCE clearly
  2. Never issue a verdict ("cheated", "guilty", etc.)
  3. Always end with the teacher-determination disclaimer
  4. Only reference policy text that was retrieved (RAG) — never invented

The structure is validated here before being sent to any AI provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Evidence labels — must appear in every explanation
LABEL_EVIDENCE  = "OBSERVED EVIDENCE"
LABEL_POLICY    = "POLICY INTERPRETATION"
LABEL_INFERENCE = "AI INFERENCE"
LABEL_TEACHER   = "TEACHER DETERMINATION"

# Phrases the AI must NEVER use (checked in tests)
FORBIDDEN_PHRASES = [
    "student cheated",
    "student is guilty",
    "student definitely",
    "confirmed cheating",
    "definitely cheated",
    "proof of cheating",
    "student was cheating",
]

# Required disclaimer that must close every explanation
REQUIRED_DISCLAIMER = "final determination"


@dataclass
class IncidentPrompt:
    """Structured prompt payload for AI explanation."""
    session_id: str
    exam_title: str
    risk_score: int
    risk_level: str
    events: list[dict[str, Any]]
    incident_summary: str        # from MCP create_incident_summary
    policy_context: str          # from RAG retrieve_policy_context
    ai_detection_signals: list[dict[str, Any]] = field(default_factory=list)
    correlation_timeline: list[dict[str, Any]] = field(default_factory=list)

    def build(self) -> str:
        """
        Render the structured prompt string.
        Returns a string with clearly labelled sections.
        """
        parts: list[str] = []

        # ── System constraints reminder ──────────────────────────────────────
        parts.append(
            "You are producing an incident explanation for a teacher reviewer.\n"
            "Structure your response in three clearly labelled sections:\n"
            f"  [{LABEL_EVIDENCE}]\n"
            f"  [{LABEL_POLICY}]\n"
            f"  [{LABEL_INFERENCE}]\n"
            "Do NOT issue a verdict or accusation. "
            "Do NOT make a determination of academic misconduct. "
            "End with: 'The final determination belongs to the reviewing teacher.'"
        )
        parts.append("")

        # ── MCP incident summary ──────────────────────────────────────────────
        if self.incident_summary:
            parts.append("=== INCIDENT SUMMARY (MCP Rules Engine — deterministic) ===")
            parts.append(self.incident_summary)
            parts.append("")

        # ── Session metadata ──────────────────────────────────────────────────
        parts.append("=== SESSION DETAILS ===")
        parts.append(f"Session ID  : {self.session_id}")
        parts.append(f"Exam        : {self.exam_title}")
        parts.append(f"Risk Score  : {self.risk_score}/100")
        parts.append(f"Risk Level  : {self.risk_level}")
        parts.append(f"Event Count : {len(self.events)}")
        parts.append("")

        # ── Event timeline (observed evidence) ───────────────────────────────
        if self.events:
            parts.append(f"=== [{LABEL_EVIDENCE}] — EVENT TIMELINE ===")
            for ev in self.events[:30]:
                ts  = ev.get("occurred_at") or ev.get("timestamp", "")
                typ = ev.get("event_type", ev.get("type", "UNKNOWN"))
                meta = ev.get("metadata") or {}
                detail = ""
                if meta.get("url"):
                    detail = f"  url={meta['url']}"
                elif meta.get("paste_length"):
                    detail = f"  chars={meta['paste_length']}"
                parts.append(f"  {ts}  {typ}{detail}")
            if len(self.events) > 30:
                parts.append(f"  ... and {len(self.events) - 30} additional events")
            parts.append("")

        # ── AI assistant detection results ────────────────────────────────────
        if self.ai_detection_signals:
            parts.append(f"=== [{LABEL_EVIDENCE}] — AI ASSISTANT DETECTION SIGNALS ===")
            for sig in self.ai_detection_signals:
                name   = sig.get("assistant_name", "Unknown")
                state  = sig.get("detection_state", "UNOBSERVABLE")
                conf   = sig.get("confidence", 0.0)
                parts.append(f"  {name}: {state} (confidence={conf:.2f})")
            parts.append("")

        # ── Correlation timeline ──────────────────────────────────────────────
        if self.correlation_timeline:
            parts.append(f"=== [{LABEL_EVIDENCE}] — BEHAVIORAL SEQUENCE CORRELATIONS ===")
            for item in self.correlation_timeline[:10]:
                seq  = item.get("sequence_name", item.get("type", ""))
                score = item.get("bonus_score", item.get("score", 0))
                parts.append(f"  {seq}  (+{score} correlation bonus)")
            parts.append("")

        # ── Retrieved policy context ──────────────────────────────────────────
        if self.policy_context:
            parts.append(f"=== [{LABEL_POLICY}] — RETRIEVED POLICY (do not modify or extend) ===")
            parts.append(self.policy_context)
            parts.append(
                "IMPORTANT: The above policy text is RETRIEVED from institutional documents. "
                "Do not paraphrase, extend, or invent additional policy statements."
            )
            parts.append("")

        # ── Final instruction ─────────────────────────────────────────────────
        parts.append("=== EXPLANATION REQUEST ===")
        parts.append(
            "Based ONLY on the evidence listed above:\n"
            f"1. Summarise the [{LABEL_EVIDENCE}] — what was actually observed.\n"
            f"2. Identify the relevant [{LABEL_POLICY}] that applies.\n"
            f"3. State your [{LABEL_INFERENCE}] — what the pattern may indicate, with appropriate uncertainty.\n"
            "4. If evidence is weak or ambiguous, say so explicitly.\n"
            "5. Close with: 'The final determination belongs to the reviewing teacher.'"
        )

        return "\n".join(parts)

    def validate(self) -> list[str]:
        """
        Return a list of validation issues (empty = valid).
        Checked before sending to any AI provider.
        """
        issues: list[str] = []
        if not self.session_id:
            issues.append("session_id is required")
        if self.risk_score < 0 or self.risk_score > 100:
            issues.append(f"risk_score out of range: {self.risk_score}")
        if not self.risk_level:
            issues.append("risk_level is required")
        return issues


def build_incident_prompt(
    session_id: str,
    exam_title: str,
    risk_score: int,
    risk_level: str,
    events: list[dict[str, Any]],
    incident_summary: str,
    policy_context: str,
    ai_detection_signals: list[dict[str, Any]] | None = None,
    correlation_timeline: list[dict[str, Any]] | None = None,
) -> IncidentPrompt:
    """Factory — builds and validates an IncidentPrompt."""
    prompt = IncidentPrompt(
        session_id=session_id,
        exam_title=exam_title,
        risk_score=risk_score,
        risk_level=risk_level,
        events=events,
        incident_summary=incident_summary,
        policy_context=policy_context,
        ai_detection_signals=ai_detection_signals or [],
        correlation_timeline=correlation_timeline or [],
    )
    return prompt
