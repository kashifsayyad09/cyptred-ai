"""
Phase 5 — AI Assistant Detection Tests

Covers:
  - Registry: all 6 assistants present, ParakeetAI primary, domain lookup
  - Signals: domain_navigation, focus_copy_paste, rapid_large_paste,
             repeated_navigation, keyboard_pattern
  - Detector: DETECTED / SUSPECTED / NOT_DETECTED / UNOBSERVABLE states
  - False-positive checks: normal exam behavior should not trigger DETECTED
  - ParakeetAI-specific: evasion risk = critical → UNOBSERVABLE on no signals
  - detect_ai_assistants MCP tool
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from mcp.detectors.ai_assistant_detector.registry import (
    REGISTRY, get_all_domains, find_by_domain, is_monitored_domain,
)
from mcp.detectors.ai_assistant_detector.signals import (
    signal_domain_navigation,
    signal_focus_copy_paste_sequence,
    signal_rapid_large_paste,
    signal_repeated_navigation,
    signal_keyboard_pattern,
)
from mcp.detectors.ai_assistant_detector.detector import (
    AIAssistantDetector, DetectionState,
)
from mcp.tools.handlers import detect_ai_assistants, check_ai_assistant_signal


# ── Test helpers ──────────────────────────────────────────────────────────────

def ev(event_type, occurred_at="2024-01-01T10:00:00Z", meta=None, source="extension"):
    return {"event_type": event_type, "occurred_at": occurred_at, "source": source, "metadata": meta or {}}


def nav_ev(url, ts="2024-01-01T10:00:05Z"):
    return ev("TAB_SWITCH", ts, {"toUrl": url})


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_six_assistants_registered(self):
        assert len(REGISTRY) == 6

    def test_parakeetai_is_first(self):
        assert REGISTRY[0].name == "ParakeetAI"

    def test_parakeetai_evasion_risk_critical(self):
        entry = next(e for e in REGISTRY if e.name == "ParakeetAI")
        assert entry.evasion_risk == "critical"

    def test_all_required_assistants_present(self):
        names = {e.name for e in REGISTRY}
        required = {"ParakeetAI", "ChatGPT", "Claude", "Gemini", "Microsoft Copilot", "Perplexity"}
        assert required == names

    def test_find_parakeetai_primary_domain(self):
        entry = find_by_domain("parakeet-ai.com")
        assert entry is not None
        assert entry.name == "ParakeetAI"

    def test_find_parakeetai_alias(self):
        entry = find_by_domain("www.parakeet-ai.com")
        assert entry is not None
        assert entry.name == "ParakeetAI"

    def test_find_parakeetai_app_subdomain(self):
        entry = find_by_domain("app.parakeet-ai.com")
        assert entry is not None
        assert entry.name == "ParakeetAI"

    def test_find_chatgpt(self):
        entry = find_by_domain("chat.openai.com")
        assert entry is not None
        assert entry.name == "ChatGPT"

    def test_find_claude(self):
        assert find_by_domain("claude.ai").name == "Claude"

    def test_find_gemini(self):
        assert find_by_domain("gemini.google.com").name == "Gemini"

    def test_find_copilot(self):
        assert find_by_domain("copilot.microsoft.com").name == "Microsoft Copilot"

    def test_find_perplexity(self):
        assert find_by_domain("perplexity.ai").name == "Perplexity"

    def test_unknown_domain_returns_none(self):
        assert find_by_domain("example.com") is None

    def test_is_monitored_true(self):
        assert is_monitored_domain("parakeet-ai.com") is True

    def test_is_monitored_false(self):
        assert is_monitored_domain("example.com") is False

    def test_get_all_domains_includes_primaries(self):
        domains = get_all_domains()
        for entry in REGISTRY:
            assert entry.primary_domain in domains

    def test_get_all_domains_includes_aliases(self):
        domains = get_all_domains()
        assert "www.parakeet-ai.com" in domains
        assert "chatgpt.com" in domains


# ── Signals ───────────────────────────────────────────────────────────────────

class TestSignals:
    def test_domain_navigation_detects_chatgpt(self):
        events = [nav_ev("https://chat.openai.com/chat")]
        results = signal_domain_navigation(events)
        assert len(results) == 1
        assert results[0].assistant == "ChatGPT"
        assert results[0].triggered is True
        assert results[0].confidence >= 0.80

    def test_domain_navigation_detects_parakeetai(self):
        events = [nav_ev("https://app.parakeet-ai.com")]
        results = signal_domain_navigation(events)
        assert len(results) == 1
        assert results[0].assistant == "ParakeetAI"

    def test_domain_navigation_ignores_non_ai_urls(self):
        events = [nav_ev("https://example.com")]
        assert signal_domain_navigation(events) == []

    def test_domain_navigation_ignores_non_nav_events(self):
        events = [ev("PASTE", meta={"pasteLength": 100})]
        assert signal_domain_navigation(events) == []

    def test_focus_copy_paste_sequence_detected(self):
        events = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("PASTE",      "2024-01-01T10:00:30Z", {"pasteLength": 200}),
        ]
        results = signal_focus_copy_paste_sequence(events)
        assert len(results) >= 1
        assert results[0].triggered is True

    def test_focus_paste_with_copy_higher_confidence(self):
        base = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("PASTE",      "2024-01-01T10:00:30Z", {"pasteLength": 50}),
        ]
        with_copy = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("COPY",       "2024-01-01T10:00:20Z"),
            ev("PASTE",      "2024-01-01T10:00:30Z", {"pasteLength": 50}),
        ]
        r_base = signal_focus_copy_paste_sequence(base)
        r_copy = signal_focus_copy_paste_sequence(with_copy)
        assert r_copy[0].confidence > r_base[0].confidence

    def test_focus_paste_outside_window_not_detected(self):
        events = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("PASTE",      "2024-01-01T10:10:00Z"),  # 10 min later
        ]
        results = signal_focus_copy_paste_sequence(events)
        assert results == []

    def test_rapid_large_paste_triggered(self):
        events = [ev("PASTE", meta={"pasteLength": 300})]
        results = signal_rapid_large_paste(events)
        assert len(results) == 1
        assert results[0].triggered is True

    def test_rapid_small_paste_not_triggered(self):
        events = [ev("PASTE", meta={"pasteLength": 10})]
        results = signal_rapid_large_paste(events)
        assert results == []

    def test_repeated_navigation_triggered(self):
        events = [nav_ev("https://example.com", f"2024-01-01T10:00:0{i}Z") for i in range(4)]
        results = signal_repeated_navigation(events)
        assert len(results) == 1
        assert results[0].triggered is True

    def test_repeated_navigation_below_threshold(self):
        events = [nav_ev("https://example.com")]
        assert signal_repeated_navigation(events) == []

    def test_keyboard_f12_triggers(self):
        events = [ev("DEVTOOLS_SHORTCUT", meta={"key": "F12"})]
        results = signal_keyboard_pattern(events)
        assert len(results) == 1

    def test_keyboard_normal_key_no_trigger(self):
        events = [ev("KEYBOARD_SHORTCUT", meta={"key": "Enter", "combo": ""})]
        assert signal_keyboard_pattern(events) == []


# ── Detector ──────────────────────────────────────────────────────────────────

class TestAIAssistantDetector:
    def setup_method(self):
        self.detector = AIAssistantDetector()

    # ── DETECTED ──────────────────────────────────────────────────────────────

    def test_chatgpt_navigation_detected(self):
        events = [nav_ev("https://chat.openai.com")]
        report = self.detector.detect(events)
        assert report.overall_state == DetectionState.DETECTED
        chatgpt = next(r for r in report.per_assistant if r.assistant_name == "ChatGPT")
        assert chatgpt.detection_state == DetectionState.DETECTED

    def test_parakeetai_navigation_detected(self):
        events = [nav_ev("https://app.parakeet-ai.com")]
        report = self.detector.detect(events)
        assert report.overall_state == DetectionState.DETECTED
        pk = next(r for r in report.per_assistant if r.assistant_name == "ParakeetAI")
        assert pk.detection_state == DetectionState.DETECTED

    def test_claude_navigation_detected(self):
        events = [nav_ev("https://claude.ai")]
        report = self.detector.detect(events)
        assert report.overall_state == DetectionState.DETECTED

    def test_perplexity_detected(self):
        events = [nav_ev("https://perplexity.ai/search")]
        report = self.detector.detect(events)
        assert report.overall_state == DetectionState.DETECTED

    # ── SUSPECTED ─────────────────────────────────────────────────────────────

    def test_behavioral_only_is_suspected(self):
        """Focus loss + large paste (no domain signal) → SUSPECTED"""
        events = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("PASTE",      "2024-01-01T10:00:30Z", {"pasteLength": 300}),
        ]
        report = self.detector.detect(events)
        assert report.overall_state in (DetectionState.SUSPECTED, DetectionState.UNOBSERVABLE)

    def test_additional_score_for_detected(self):
        events = [nav_ev("https://chat.openai.com")]
        report = self.detector.detect(events)
        assert report.additional_score == 25

    def test_additional_score_for_suspected(self):
        events = [
            ev("FOCUS_LOSS", "2024-01-01T10:00:00Z"),
            ev("PASTE",      "2024-01-01T10:00:20Z", {"pasteLength": 300}),
        ]
        report = self.detector.detect(events)
        # SUSPECTED → partial score
        assert 0 <= report.additional_score < 25

    # ── NOT_DETECTED / UNOBSERVABLE ───────────────────────────────────────────

    def test_empty_events_unobservable_for_parakeetai(self):
        """ParakeetAI has critical evasion risk → UNOBSERVABLE when no signals."""
        report = self.detector.detect([])
        pk = next(r for r in report.per_assistant if r.assistant_name == "ParakeetAI")
        assert pk.detection_state == DetectionState.UNOBSERVABLE

    def test_empty_events_overall_unobservable(self):
        report = self.detector.detect([])
        assert report.overall_state == DetectionState.UNOBSERVABLE

    def test_limitation_notice_always_present(self):
        report = self.detector.detect([])
        assert "does not prove" in report.limitation_notice
        assert "teacher" in report.limitation_notice.lower()

    # ── False positive suite ──────────────────────────────────────────────────

    def test_normal_typing_no_detection(self):
        """Normal exam typing should not trigger DETECTED."""
        events = [
            ev("EXAM_STARTED"),
            ev("FOCUS_LOSS",  "2024-01-01T10:05:00Z"),
            ev("FOCUS_REGAIN","2024-01-01T10:05:05Z"),
        ]
        report = self.detector.detect(events)
        assert report.overall_state != DetectionState.DETECTED

    def test_small_paste_no_detection(self):
        """A small paste (e.g. student number) should not trigger DETECTED."""
        events = [ev("PASTE", meta={"pasteLength": 8})]
        report = self.detector.detect(events)
        assert report.overall_state != DetectionState.DETECTED

    def test_single_tab_switch_legitimate(self):
        """Single tab switch to a non-AI site should not trigger DETECTED."""
        events = [nav_ev("https://en.wikipedia.org/wiki/Algorithm")]
        report = self.detector.detect(events)
        assert report.overall_state != DetectionState.DETECTED

    def test_detection_is_deterministic(self):
        """Same events must always produce the same detection state."""
        events = [nav_ev("https://chat.openai.com")]
        r1 = self.detector.detect(events)
        r2 = self.detector.detect(events)
        assert r1.overall_state == r2.overall_state
        assert r1.overall_confidence == r2.overall_confidence


# ── MCP detect_ai_assistants tool ─────────────────────────────────────────────

class TestDetectAIAssistantsTool:
    def test_tool_returns_overall_state(self):
        events = [nav_ev("https://chat.openai.com")]
        r = detect_ai_assistants({"events": events, "session_id": "sess-1"})
        assert r["overall_state"] == "DETECTED"
        assert r["additional_score"] == 25

    def test_tool_returns_limitation_notice(self):
        r = detect_ai_assistants({"events": []})
        assert "limitation_notice" in r
        assert "does not prove" in r["limitation_notice"]

    def test_tool_returns_per_assistant_list(self):
        r = detect_ai_assistants({"events": []})
        assert len(r["per_assistant"]) == 6
        names = [a["name"] for a in r["per_assistant"]]
        assert "ParakeetAI" in names
        assert "ChatGPT" in names

    def test_tool_returns_signals_triggered(self):
        events = [nav_ev("https://perplexity.ai")]
        r = detect_ai_assistants({"events": events})
        assert isinstance(r["signals_triggered"], list)
        assert len(r["signals_triggered"]) >= 1

    def test_check_ai_assistant_signal_detected(self):
        r = check_ai_assistant_signal({
            "detection_state": "DETECTED",
            "assistant_name": "ParakeetAI",
            "domain": "parakeet-ai.com",
            "confidence": 0.9,
        })
        assert r["score_contribution"] == 25
        assert r["severity"] == "critical"

    def test_check_ai_assistant_signal_unobservable_zero_score(self):
        r = check_ai_assistant_signal({"detection_state": "UNOBSERVABLE"})
        assert r["score_contribution"] == 0
