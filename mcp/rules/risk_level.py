"""
Deterministic Risk Engine — classifies a numeric score into a risk level.

LLMs do NOT set numerical scores. This module is the single source of truth
for score → level mapping.
"""

from __future__ import annotations

from enum import Enum

from mcp.config import RiskThresholds, load_thresholds


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    MONITORING = "MONITORING"
    ATTENTION = "ATTENTION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_PRIORITY_REVIEW = "HIGH_PRIORITY_REVIEW"


def classify(score: int, thresholds: RiskThresholds | None = None) -> RiskLevel:
    """
    Deterministically map a risk score to a RiskLevel.

    Uses thresholds from environment (or provided override).
    Score is clamped to [0, 100] before classification.
    """
    t = thresholds or load_thresholds()
    s = max(0, min(100, score))

    if s >= t.high_priority:
        return RiskLevel.HIGH_PRIORITY_REVIEW
    if s >= t.review_required:
        return RiskLevel.REVIEW_REQUIRED
    if s >= t.attention:
        return RiskLevel.ATTENTION
    if s >= t.monitoring:
        return RiskLevel.MONITORING
    return RiskLevel.NORMAL
