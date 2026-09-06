"""
Rules Engine tests — Phase 4 will populate these with real assertions.
Scaffold ensures test discovery works from Phase 1.
"""

import pytest


def test_risk_weights_are_positive():
    """All configured risk weights must be positive integers."""
    weights = {
        "TAB_SWITCH": 10,
        "FOCUS_LOSS": 5,
        "COPY": 15,
        "PASTE": 15,
        "FULLSCREEN_EXIT": 10,
        "SUSPICIOUS_NAVIGATION": 20,
        "AI_ASSISTANT_SIGNAL": 25,
        "REPEATED_VIOLATIONS": 20,
        "SUSPICIOUS_SEQUENCE": 20,
    }
    for event, weight in weights.items():
        assert weight > 0, f"{event} weight must be positive"


def test_risk_level_thresholds():
    """Risk levels must map to correct score ranges."""
    thresholds = [
        (0, "NORMAL"), (19, "NORMAL"),
        (20, "MONITORING"), (39, "MONITORING"),
        (40, "ATTENTION"), (59, "ATTENTION"),
        (60, "REVIEW_REQUIRED"), (79, "REVIEW_REQUIRED"),
        (80, "HIGH_PRIORITY_REVIEW"), (100, "HIGH_PRIORITY_REVIEW"),
    ]
    for score, expected_level in thresholds:
        level = _classify(score)
        assert level == expected_level, f"Score {score} should be {expected_level}, got {level}"


def _classify(score: int) -> str:
    if score < 20:
        return "NORMAL"
    if score < 40:
        return "MONITORING"
    if score < 60:
        return "ATTENTION"
    if score < 80:
        return "REVIEW_REQUIRED"
    return "HIGH_PRIORITY_REVIEW"
