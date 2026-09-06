"""
MCP Server configuration — all scoring weights loaded from environment.
Never hardcoded anywhere else in the codebase.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskWeights:
    tab_switch: int
    focus_loss: int
    copy: int
    paste: int
    fullscreen_exit: int
    suspicious_navigation: int
    ai_assistant_signal: int
    repeated_violations: int
    suspicious_sequence: int


@dataclass(frozen=True)
class RiskThresholds:
    monitoring: int        # score >= this → MONITORING
    attention: int         # score >= this → ATTENTION
    review_required: int   # score >= this → REVIEW_REQUIRED
    high_priority: int     # score >= this → HIGH_PRIORITY_REVIEW


def _int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def load_weights() -> RiskWeights:
    return RiskWeights(
        tab_switch=_int("RISK_WEIGHT_TAB_SWITCH", 10),
        focus_loss=_int("RISK_WEIGHT_FOCUS_LOSS", 5),
        copy=_int("RISK_WEIGHT_COPY", 15),
        paste=_int("RISK_WEIGHT_PASTE", 15),
        fullscreen_exit=_int("RISK_WEIGHT_FULLSCREEN_EXIT", 10),
        suspicious_navigation=_int("RISK_WEIGHT_SUSPICIOUS_NAVIGATION", 20),
        ai_assistant_signal=_int("RISK_WEIGHT_AI_ASSISTANT_SIGNAL", 25),
        repeated_violations=_int("RISK_WEIGHT_REPEATED_VIOLATIONS", 20),
        suspicious_sequence=_int("RISK_WEIGHT_SUSPICIOUS_SEQUENCE", 20),
    )


def load_thresholds() -> RiskThresholds:
    return RiskThresholds(
        monitoring=_int("RISK_THRESHOLD_MONITORING", 20),
        attention=_int("RISK_THRESHOLD_ATTENTION", 40),
        review_required=_int("RISK_THRESHOLD_REVIEW_REQUIRED", 60),
        high_priority=_int("RISK_THRESHOLD_HIGH_PRIORITY", 80),
    )
