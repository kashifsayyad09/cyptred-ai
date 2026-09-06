"""
Phase 4 — MCP Server + Rules Engine Tests

All tests are pure-Python, no network calls, no Docker required.
Tests cover:
  - Risk level classification
  - Rules engine scoring
  - Correlation engine sequences
  - All 15 MCP tool handlers
  - Edge cases (empty events, capped scores, unknown events)
  - Critical requirement: rules engine works without AI providers
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from mcp.config import load_weights, load_thresholds, RiskWeights, RiskThresholds
from mcp.rules.risk_level import RiskLevel, classify
from mcp.rules.rules_engine import RulesEngine, EventType
from mcp.correlation.engine import CorrelationEngine, KNOWN_SEQUENCES
from mcp.tools.handlers import (
    check_focus_loss, check_tab_switch, check_copy, check_paste,
    check_navigation, check_fullscreen, check_keyboard_shortcuts,
    check_devtools_signal, check_ai_assistant_signal,
    correlate_behavior, calculate_risk, get_exam_rules,
    get_policy, get_student_timeline, create_incident_summary,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_EVENTS = [
    {"event_type": "FOCUS_LOSS",           "occurred_at": "2024-01-01T10:00:05Z", "source": "extension", "metadata": {}},
    {"event_type": "TAB_SWITCH",           "occurred_at": "2024-01-01T10:00:10Z", "source": "extension", "metadata": {"toUrl": "https://chat.openai.com"}},
    {"event_type": "AI_ASSISTANT_SIGNAL",  "occurred_at": "2024-01-01T10:00:15Z", "source": "mcp",       "metadata": {"assistant_name": "ChatGPT", "domain": "chat.openai.com", "detection_state": "DETECTED"}},
    {"event_type": "COPY",                 "occurred_at": "2024-01-01T10:00:30Z", "source": "extension", "metadata": {}},
    {"event_type": "PASTE",                "occurred_at": "2024-01-01T10:00:35Z", "source": "extension", "metadata": {"pasteLength": 350}},
]


# ── Risk Level Classification ─────────────────────────────────────────────────

class TestRiskLevelClassification:
    def test_normal_lower_bound(self):
        assert classify(0) == RiskLevel.NORMAL

    def test_normal_upper_bound(self):
        assert classify(19) == RiskLevel.NORMAL

    def test_monitoring_lower(self):
        assert classify(20) == RiskLevel.MONITORING

    def test_monitoring_upper(self):
        assert classify(39) == RiskLevel.MONITORING

    def test_attention_lower(self):
        assert classify(40) == RiskLevel.ATTENTION

    def test_attention_upper(self):
        assert classify(59) == RiskLevel.ATTENTION

    def test_review_required_lower(self):
        assert classify(60) == RiskLevel.REVIEW_REQUIRED

    def test_review_required_upper(self):
        assert classify(79) == RiskLevel.REVIEW_REQUIRED

    def test_high_priority_lower(self):
        assert classify(80) == RiskLevel.HIGH_PRIORITY_REVIEW

    def test_high_priority_at_100(self):
        assert classify(100) == RiskLevel.HIGH_PRIORITY_REVIEW

    def test_score_clamped_above_100(self):
        # classify clamps before comparing
        assert classify(150) == RiskLevel.HIGH_PRIORITY_REVIEW

    def test_score_clamped_below_0(self):
        assert classify(-10) == RiskLevel.NORMAL

    def test_custom_thresholds(self):
        t = RiskThresholds(monitoring=10, attention=30, review_required=50, high_priority=70)
        assert classify(10, t) == RiskLevel.MONITORING
        assert classify(9, t) == RiskLevel.NORMAL


# ── Rules Engine ──────────────────────────────────────────────────────────────

class TestRulesEngine:
    def setup_method(self):
        self.engine = RulesEngine()

    def test_empty_events_zero_score(self):
        result = self.engine.evaluate([])
        assert result.total_score == 0
        assert result.risk_level == RiskLevel.NORMAL

    def test_tab_switch_scored(self):
        events = [{"event_type": EventType.TAB_SWITCH, "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}}]
        result = self.engine.evaluate(events)
        assert result.total_score == 10

    def test_focus_loss_scored(self):
        events = [{"event_type": EventType.FOCUS_LOSS, "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}}]
        result = self.engine.evaluate(events)
        assert result.total_score == 5

    def test_ai_signal_highest_weight(self):
        events = [{"event_type": EventType.AI_ASSISTANT_SIGNAL, "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}}]
        result = self.engine.evaluate(events)
        assert result.total_score == 25

    def test_multiple_events_accumulate(self):
        result = self.engine.evaluate(SAMPLE_EVENTS)
        # FOCUS_LOSS(5) + TAB_SWITCH(10) + AI_SIGNAL(25) + COPY(15) + PASTE(15) = 70
        assert result.total_score == 70
        assert result.risk_level == RiskLevel.REVIEW_REQUIRED

    def test_score_capped_at_100(self):
        many_events = [
            {"event_type": EventType.AI_ASSISTANT_SIGNAL, "occurred_at": f"2024-01-01T10:00:{i:02d}Z", "metadata": {}}
            for i in range(10)
        ]
        result = self.engine.evaluate(many_events)
        assert result.total_score == 100

    def test_unknown_events_not_scored(self):
        events = [{"event_type": "UNKNOWN_FUTURE_EVENT", "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}}]
        result = self.engine.evaluate(events)
        assert result.total_score == 0

    def test_custom_weights(self):
        weights = RiskWeights(
            tab_switch=1, focus_loss=1, copy=1, paste=1,
            fullscreen_exit=1, suspicious_navigation=1,
            ai_assistant_signal=1, repeated_violations=1, suspicious_sequence=1,
        )
        engine = RulesEngine(weights=weights)
        events = [{"event_type": EventType.TAB_SWITCH, "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}}]
        result = engine.evaluate(events)
        assert result.total_score == 1

    def test_rules_engine_works_without_ai_providers(self):
        """
        CRITICAL: The rules engine must be fully deterministic and work
        even when Groq and NVIDIA are both unavailable.
        """
        result = self.engine.evaluate(SAMPLE_EVENTS)
        assert result.risk_level is not None
        assert isinstance(result.total_score, int)
        assert 0 <= result.total_score <= 100

    def test_paste_note_generated(self):
        events = [
            {"event_type": EventType.AI_ASSISTANT_SIGNAL, "occurred_at": "2024-01-01T10:00:00Z", "metadata": {}},
            {"event_type": EventType.PASTE,               "occurred_at": "2024-01-01T10:00:05Z", "metadata": {}},
        ]
        result = self.engine.evaluate(events)
        assert any("AI assistant" in n for n in result.notes)


# ── Correlation Engine ────────────────────────────────────────────────────────

class TestCorrelationEngine:
    def setup_method(self):
        self.engine = CorrelationEngine()

    def test_empty_events_no_timeline(self):
        result = self.engine.correlate([])
        assert result.timeline == []
        assert result.matched_sequences == []
        assert result.sequence_bonus == 0

    def test_timeline_sorted_chronologically(self):
        events = [
            {"event_type": "PASTE",      "occurred_at": "2024-01-01T10:00:10Z", "source": "extension", "metadata": {}},
            {"event_type": "FOCUS_LOSS", "occurred_at": "2024-01-01T10:00:05Z", "source": "extension", "metadata": {}},
        ]
        result = self.engine.correlate(events)
        assert result.timeline[0].event_type == "FOCUS_LOSS"
        assert result.timeline[1].event_type == "PASTE"

    def test_ai_navigation_paste_sequence_detected(self):
        events = [
            {"event_type": "AI_ASSISTANT_SIGNAL", "occurred_at": "2024-01-01T10:00:00Z", "source": "mcp", "metadata": {}},
            {"event_type": "PASTE",               "occurred_at": "2024-01-01T10:00:05Z", "source": "extension", "metadata": {}},
        ]
        result = self.engine.correlate(events)
        names = [s.name for s in result.matched_sequences]
        assert "ai_navigation_paste" in names
        assert result.sequence_bonus > 0

    def test_sequence_outside_time_window_not_matched(self):
        events = [
            {"event_type": "AI_ASSISTANT_SIGNAL", "occurred_at": "2024-01-01T09:00:00Z", "source": "mcp", "metadata": {}},
            # 10 minutes later — outside 5-minute window
            {"event_type": "PASTE", "occurred_at": "2024-01-01T09:10:00Z", "source": "extension", "metadata": {}},
        ]
        result = self.engine.correlate(events)
        names = [s.name for s in result.matched_sequences]
        assert "ai_navigation_paste" not in names

    def test_sequence_bonus_capped_at_40(self):
        # Trigger every known sequence simultaneously
        events = [
            {"event_type": "AI_ASSISTANT_SIGNAL",  "occurred_at": "2024-01-01T10:00:00Z", "source": "mcp", "metadata": {}},
            {"event_type": "FOCUS_LOSS",            "occurred_at": "2024-01-01T10:00:01Z", "source": "extension", "metadata": {}},
            {"event_type": "SUSPICIOUS_NAVIGATION", "occurred_at": "2024-01-01T10:00:02Z", "source": "extension", "metadata": {}},
            {"event_type": "TAB_SWITCH",            "occurred_at": "2024-01-01T10:00:03Z", "source": "extension", "metadata": {}},
            {"event_type": "COPY",                  "occurred_at": "2024-01-01T10:00:04Z", "source": "extension", "metadata": {}},
            {"event_type": "PASTE",                 "occurred_at": "2024-01-01T10:00:05Z", "source": "extension", "metadata": {}},
            {"event_type": "DEVTOOLS_SHORTCUT",     "occurred_at": "2024-01-01T10:00:06Z", "source": "extension", "metadata": {}},
        ]
        result = self.engine.correlate(events)
        assert result.sequence_bonus <= 40


# ── MCP Tool Handlers ─────────────────────────────────────────────────────────

class TestMCPToolHandlers:
    def test_all_tools_registered(self):
        from mcp.tools import TOOL_REGISTRY
        required = {
            "check_focus_loss", "check_tab_switch", "check_copy", "check_paste",
            "check_navigation", "check_fullscreen", "check_keyboard_shortcuts",
            "check_devtools_signal", "check_ai_assistant_signal",
            "detect_ai_assistants",
            "correlate_behavior", "calculate_risk", "get_exam_rules",
            "get_policy", "get_student_timeline", "create_incident_summary",
        }
        missing = required - set(TOOL_REGISTRY.keys())
        assert not missing, f"Missing tools: {missing}"

    def test_check_focus_loss(self):
        r = check_focus_loss({"count": 1})
        assert r["tool"] == "check_focus_loss"
        assert r["score_contribution"] >= 0
        assert "severity" in r

    def test_check_focus_loss_repeated(self):
        r = check_focus_loss({"count": 5})
        assert r["severity"] == "medium"
        assert "Repeated" in r["finding"]

    def test_check_tab_switch(self):
        r = check_tab_switch({"count": 2, "to_url": "https://chat.openai.com"})
        assert r["score_contribution"] == 20

    def test_check_copy(self):
        r = check_copy({"count": 1})
        assert r["score_contribution"] == 15

    def test_check_paste_large(self):
        r = check_paste({"count": 1, "max_paste_length": 500})
        assert r["severity"] == "high"
        assert "500" in r["finding"]

    def test_check_paste_small(self):
        r = check_paste({"count": 1, "max_paste_length": 10})
        assert r["severity"] == "medium"

    def test_check_navigation(self):
        r = check_navigation({"count": 2, "urls": ["https://chat.openai.com"]})
        assert r["score_contribution"] == 40

    def test_check_fullscreen_required(self):
        r = check_fullscreen({"count": 1, "fullscreen_required": True})
        assert r["score_contribution"] == 10

    def test_check_fullscreen_not_required(self):
        r = check_fullscreen({"count": 1, "fullscreen_required": False})
        assert r["score_contribution"] == 0

    def test_check_devtools(self):
        r = check_devtools_signal({"count": 1, "keys": ["F12"]})
        assert r["score_contribution"] > 0
        assert r["severity"] == "high"

    def test_check_ai_signal_detected(self):
        r = check_ai_assistant_signal({
            "detection_state": "DETECTED",
            "assistant_name": "ParakeetAI",
            "domain": "parakeet-ai.com",
            "confidence": 0.9,
        })
        assert r["score_contribution"] == 25
        assert r["severity"] == "critical"

    def test_check_ai_signal_suspected(self):
        r = check_ai_assistant_signal({
            "detection_state": "SUSPECTED",
            "assistant_name": "ChatGPT",
            "domain": "chat.openai.com",
            "confidence": 0.6,
        })
        assert r["score_contribution"] == 12  # 25 // 2

    def test_check_ai_signal_unobservable(self):
        r = check_ai_assistant_signal({"detection_state": "UNOBSERVABLE"})
        assert r["score_contribution"] == 0
        assert "does not prove" in r["finding"]

    def test_calculate_risk_full_scenario(self):
        r = calculate_risk({"events": SAMPLE_EVENTS})
        assert r["score"] >= 70
        assert r["risk_level"] in ("REVIEW_REQUIRED", "HIGH_PRIORITY_REVIEW")
        assert isinstance(r["contributing_events"], list)

    def test_calculate_risk_empty_events(self):
        r = calculate_risk({"events": []})
        assert r["score"] == 0
        assert r["risk_level"] == "NORMAL"

    def test_get_exam_rules_returns_all_weights(self):
        r = get_exam_rules({})
        weights = r["weights"]
        expected_keys = {
            "tab_switch", "focus_loss", "copy", "paste", "fullscreen_exit",
            "suspicious_navigation", "ai_assistant_signal",
            "repeated_violations", "suspicious_sequence",
        }
        assert expected_keys == set(weights.keys())

    def test_get_policy_returns_ai_prohibition(self):
        r = get_policy({"exam_id": "test-123"})
        assert "AI assistants" in r["policy_summary"]
        assert "ParakeetAI" in r["policy_summary"]

    def test_get_student_timeline(self):
        r = get_student_timeline({"session_id": "sess-1", "events": SAMPLE_EVENTS})
        assert r["event_count"] == len(SAMPLE_EVENTS)
        assert isinstance(r["timeline"], list)

    def test_create_incident_summary_structure(self):
        r = create_incident_summary({
            "session_id": "sess-1",
            "student_id": "stu-1",
            "events": SAMPLE_EVENTS,
            "risk_score": 70,
            "risk_level": "REVIEW_REQUIRED",
            "exam_title": "Test Exam",
        })
        assert "observed_evidence" in r
        assert "ai_prompt_context" in r
        assert "OBSERVED EVIDENCE" in r["important"]
        assert "no automated verdict" in r["important"].lower() or "No automated" in r["important"]

    def test_correlate_behavior(self):
        r = correlate_behavior({"events": SAMPLE_EVENTS})
        assert "timeline" in r
        assert "matched_sequences" in r
        assert r["timeline_length"] == len(SAMPLE_EVENTS)

    def test_rules_engine_deterministic_same_result(self):
        """Same events must always produce the same score — no randomness."""
        engine = RulesEngine()
        r1 = engine.evaluate(SAMPLE_EVENTS)
        r2 = engine.evaluate(SAMPLE_EVENTS)
        assert r1.total_score == r2.total_score
        assert r1.risk_level == r2.risk_level
