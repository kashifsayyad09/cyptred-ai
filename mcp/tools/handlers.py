"""
MCP Tool Handlers — all 15 tools exposed by the MCP server.

Each tool is a pure function that accepts a validated dict payload
and returns a structured dict result.  No side effects.

Tools:
  check_focus_loss          check_tab_switch
  check_copy                check_paste
  check_navigation          check_fullscreen
  check_keyboard_shortcuts  check_devtools_signal
  check_ai_assistant_signal correlate_behavior
  calculate_risk            get_exam_rules
  get_policy                get_student_timeline
  create_incident_summary
"""

from __future__ import annotations

from typing import Any

from mcp.config import load_weights, load_thresholds
from mcp.rules.rules_engine import RulesEngine, EventType
from mcp.rules.risk_level import classify
from mcp.correlation.engine import CorrelationEngine
from mcp.detectors.ai_assistant_detector import AIAssistantDetector, DetectionState


# ── Shared singletons ─────────────────────────────────────────────────────────
_engine = RulesEngine()
_correlator = CorrelationEngine()
_ai_detector = AIAssistantDetector()


# ── Individual event checks ───────────────────────────────────────────────────

def check_focus_loss(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single focus-loss or window-blur event."""
    count = int(payload.get("count", 1))
    w = load_weights()
    score = min(w.focus_loss * count, 30)
    return {
        "tool": "check_focus_loss",
        "event_count": count,
        "score_contribution": score,
        "severity": "medium" if count >= 3 else "low",
        "finding": (
            f"Focus lost {count} time(s). "
            + ("Repeated focus losses may indicate attention outside exam." if count >= 3 else "")
        ),
    }


def check_tab_switch(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate tab-switch events."""
    count = int(payload.get("count", 1))
    to_url = payload.get("to_url", "")
    w = load_weights()
    score = min(w.tab_switch * count, 40)
    return {
        "tool": "check_tab_switch",
        "event_count": count,
        "to_url": to_url,
        "score_contribution": score,
        "severity": "medium",
        "finding": f"Student switched tabs {count} time(s).",
    }


def check_copy(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate copy events."""
    count = int(payload.get("count", 1))
    w = load_weights()
    score = min(w.copy * count, 30)
    return {
        "tool": "check_copy",
        "event_count": count,
        "score_contribution": score,
        "severity": "medium",
        "finding": f"Copy event(s) detected: {count}.",
    }


def check_paste(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate paste events. Paste length is an additional signal."""
    count = int(payload.get("count", 1))
    max_len = int(payload.get("max_paste_length", 0))
    w = load_weights()
    score = min(w.paste * count, 30)
    severity = "high" if max_len > 200 else "medium"
    return {
        "tool": "check_paste",
        "event_count": count,
        "max_paste_length": max_len,
        "score_contribution": score,
        "severity": severity,
        "finding": (
            f"Paste event(s) detected: {count}. "
            + (f"Largest paste was {max_len} characters — unusually long." if max_len > 200 else "")
        ),
    }


def check_navigation(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate navigation-away events."""
    urls = payload.get("urls", [])
    count = int(payload.get("count", len(urls)))
    w = load_weights()
    score = min(w.suspicious_navigation * count, 40)
    return {
        "tool": "check_navigation",
        "event_count": count,
        "urls_observed": urls[:5],  # cap list for response size
        "score_contribution": score,
        "severity": "high",
        "finding": f"Student navigated away from exam {count} time(s).",
    }


def check_fullscreen(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate fullscreen-exit events."""
    count = int(payload.get("count", 1))
    required = bool(payload.get("fullscreen_required", True))
    w = load_weights()
    score = (w.fullscreen_exit * count) if required else 0
    return {
        "tool": "check_fullscreen",
        "event_count": count,
        "fullscreen_required": required,
        "score_contribution": score,
        "severity": "medium" if required else "low",
        "finding": (
            f"Fullscreen exited {count} time(s). "
            + ("Fullscreen is required for this exam." if required else "Fullscreen not required.")
        ),
    }


def check_keyboard_shortcuts(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate suspicious keyboard shortcuts."""
    combos = payload.get("combos", [])
    count = int(payload.get("count", len(combos)))
    return {
        "tool": "check_keyboard_shortcuts",
        "event_count": count,
        "combos_observed": combos[:10],
        "score_contribution": min(5 * count, 20),
        "severity": "low",
        "finding": f"Suspicious keyboard shortcut(s) recorded: {count}.",
    }


def check_devtools_signal(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate DevTools open signals."""
    keys = payload.get("keys", [])
    count = int(payload.get("count", len(keys)))
    w = load_weights()
    score = min(w.suspicious_navigation * count, 30)
    return {
        "tool": "check_devtools_signal",
        "event_count": count,
        "keys_observed": keys[:5],
        "score_contribution": score,
        "severity": "high",
        "finding": (
            f"DevTools shortcut(s) detected: {count}. "
            "May indicate attempt to inspect or modify exam content."
        ),
    }


# ── AI assistant detection (full Phase 5 implementation) ─────────────────────

def check_ai_assistant_signal(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a pre-computed AI detection result (from detect_ai_assistants).
    Accepts detection_state, assistant_name, domain, confidence directly.
    """
    detection_state = payload.get("detection_state", "UNOBSERVABLE")
    assistant_name  = payload.get("assistant_name", "unknown")
    domain          = payload.get("domain", "")
    confidence      = float(payload.get("confidence", 0.5))

    w = load_weights()
    score = 0
    if detection_state == "DETECTED":
        score = w.ai_assistant_signal
    elif detection_state == "SUSPECTED":
        score = w.ai_assistant_signal // 2

    severity = "critical" if detection_state == "DETECTED" else (
        "high" if detection_state == "SUSPECTED" else "low"
    )

    return {
        "tool": "check_ai_assistant_signal",
        "detection_state": detection_state,
        "assistant_name": assistant_name,
        "domain": domain,
        "confidence": confidence,
        "score_contribution": score,
        "severity": severity,
        "finding": (
            f"AI assistant signal — {assistant_name} ({domain}): {detection_state}. "
            "Absence of DETECTED does not prove the software was not used."
        ),
    }


def detect_ai_assistants(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run the full AI assistant detector over a session's event list.
    Returns: overall_state, per-assistant results, signals, score contribution.
    """
    events     = payload.get("events", [])
    session_id = payload.get("session_id", "")

    report = _ai_detector.detect(events, session_id=session_id)

    return {
        "tool": "detect_ai_assistants",
        "session_id": session_id,
        "overall_state": report.overall_state.value,
        "overall_confidence": report.overall_confidence,
        "additional_score": report.additional_score,
        "summary": report.summary,
        "limitation_notice": report.limitation_notice,
        "per_assistant": [
            {
                "name": r.assistant_name,
                "domain": r.primary_domain,
                "state": r.detection_state.value,
                "confidence": r.confidence,
                "evidence_summary": r.evidence_summary,
            }
            for r in report.per_assistant
        ],
        "signals_triggered": [
            {
                "signal_name": s.signal_name,
                "triggered": s.triggered,
                "confidence": s.confidence,
                "assistant": s.assistant,
                "domain": s.domain,
                "description": s.description,
            }
            for s in report.all_signals if s.triggered
        ],
    }


# ── Aggregated tools ──────────────────────────────────────────────────────────

def correlate_behavior(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run the correlation engine over a list of raw events.
    Returns timeline, matched sequences, and a sequence bonus weight.
    """
    events = payload.get("events", [])
    result = _correlator.correlate(events)

    return {
        "tool": "correlate_behavior",
        "timeline_length": len(result.timeline),
        "matched_sequences": [
            {"name": s.name, "description": s.description, "extra_weight": s.extra_weight}
            for s in result.matched_sequences
        ],
        "sequence_bonus": result.sequence_bonus,
        "summary": result.summary,
        "timeline": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "severity": e.severity,
                "score_contribution": e.score_contribution,
                "confidence": e.confidence,
                "description": e.description,
                "rule": e.rule,
                "metadata": e.metadata,
            }
            for e in result.timeline
        ],
    }


def calculate_risk(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run the full Rules Engine over a list of events and return the
    deterministic risk score and level.
    Sequence bonus from the correlation engine is also applied.
    """
    events = payload.get("events", [])
    exam_rules = payload.get("exam_rules", {})

    # Apply per-exam rule overrides if provided
    from mcp.config import RiskWeights
    weights_kwargs = {
        "tab_switch":           int(exam_rules.get("weight_tab_switch", 10)),
        "focus_loss":           int(exam_rules.get("weight_focus_loss", 5)),
        "copy":                 int(exam_rules.get("weight_copy", 15)),
        "paste":                int(exam_rules.get("weight_paste", 15)),
        "fullscreen_exit":      int(exam_rules.get("weight_fullscreen_exit", 10)),
        "suspicious_navigation":int(exam_rules.get("weight_suspicious_navigation", 20)),
        "ai_assistant_signal":  int(exam_rules.get("weight_ai_assistant_signal", 25)),
        "repeated_violations":  int(exam_rules.get("weight_repeated_violations", 20)),
        "suspicious_sequence":  int(exam_rules.get("weight_suspicious_sequence", 20)),
    }
    engine = RulesEngine(weights=RiskWeights(**weights_kwargs))
    rule_result = engine.evaluate(events)

    # Add sequence bonus
    corr_result = _correlator.correlate(events)
    total = min(rule_result.total_score + corr_result.sequence_bonus, 100)
    level = classify(total)

    return {
        "tool": "calculate_risk",
        "score": total,
        "risk_level": level.value,
        "base_score": rule_result.total_score,
        "sequence_bonus": corr_result.sequence_bonus,
        "contributing_events": [
            {"event_type": s.event_type, "weight": s.weight, "reason": s.reason}
            for s in rule_result.scored_events
        ],
        "notes": rule_result.notes,
        "matched_sequences": [s.name for s in corr_result.matched_sequences],
    }


def get_exam_rules(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the currently active scoring weights (from environment)."""
    w = load_weights()
    t = load_thresholds()
    return {
        "tool": "get_exam_rules",
        "weights": {
            "tab_switch":            w.tab_switch,
            "focus_loss":            w.focus_loss,
            "copy":                  w.copy,
            "paste":                 w.paste,
            "fullscreen_exit":       w.fullscreen_exit,
            "suspicious_navigation": w.suspicious_navigation,
            "ai_assistant_signal":   w.ai_assistant_signal,
            "repeated_violations":   w.repeated_violations,
            "suspicious_sequence":   w.suspicious_sequence,
        },
        "thresholds": {
            "monitoring":       t.monitoring,
            "attention":        t.attention,
            "review_required":  t.review_required,
            "high_priority":    t.high_priority,
        },
        "source": "environment_variables",
    }


def get_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return policy metadata for the exam.
    Full RAG-backed retrieval implemented in Phase 6.
    """
    exam_id = payload.get("exam_id", "")
    return {
        "tool": "get_policy",
        "exam_id": exam_id,
        "policy_summary": (
            "AI assistants (ChatGPT, Claude, Gemini, Copilot, ParakeetAI, Perplexity, "
            "and similar tools) are prohibited during this examination. "
            "External resources are not permitted. "
            "Students must remain on the examination page at all times."
        ),
        "source": "default_policy",
        "note": "Full RAG-backed policy retrieval implemented in Phase 6.",
    }


def get_student_timeline(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Build and return a formatted evidence timeline for a student session.
    """
    events = payload.get("events", [])
    session_id = payload.get("session_id", "")
    corr = _correlator.correlate(events)

    return {
        "tool": "get_student_timeline",
        "session_id": session_id,
        "event_count": len(corr.timeline),
        "timeline": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "severity": e.severity,
                "description": e.description,
                "confidence": e.confidence,
            }
            for e in corr.timeline
        ],
        "summary": corr.summary,
    }


def create_incident_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create a structured incident summary from a session's events and risk score.
    This is passed to the AI Gateway (Phase 7/8) for explanation generation.
    The summary clearly distinguishes observed evidence from inference.
    """
    session_id  = payload.get("session_id", "")
    events      = payload.get("events", [])
    risk_score  = int(payload.get("risk_score", 0))
    risk_level  = payload.get("risk_level", "NORMAL")
    exam_title  = payload.get("exam_title", "Examination")
    student_id  = payload.get("student_id", "")

    corr   = _correlator.correlate(events)
    engine = RulesEngine()
    rules  = engine.evaluate(events)

    high_events = [e for e in corr.timeline if e.severity in ("high", "critical")]

    return {
        "tool": "create_incident_summary",
        "session_id": session_id,
        "student_id": student_id,
        "exam_title": exam_title,
        "risk_score": risk_score,
        "risk_level": risk_level,
        # ── Observed evidence (factual — what was recorded) ───────────────
        "observed_evidence": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "description": e.description,
                "severity": e.severity,
                "confidence": e.confidence,
            }
            for e in high_events
        ],
        # ── Correlated sequences (deterministic analysis) ─────────────────
        "correlated_sequences": [
            {"name": s.name, "description": s.description}
            for s in corr.matched_sequences
        ],
        "rules_notes": rules.notes,
        # ── Summary for AI explanation prompt ─────────────────────────────
        "ai_prompt_context": (
            f"Session {session_id} for exam '{exam_title}' has a risk score of "
            f"{risk_score}/100 (level: {risk_level}). "
            f"Observed events: {len(corr.timeline)} total, "
            f"{len(high_events)} high/critical severity. "
            f"Correlated sequences: {[s.name for s in corr.matched_sequences]}. "
            f"Deterministic rules notes: {rules.notes}. "
            "Explain why this session warrants review without accusing the student."
        ),
        "important": (
            "The evidence above is OBSERVED (recorded by the browser extension). "
            "AI explanation must distinguish OBSERVED EVIDENCE from POLICY INTERPRETATION "
            "from AI INFERENCE. No automated verdict should be issued."
        ),
    }
