"""
AI Assistant Detector package.

Usage:
    from mcp.detectors.ai_assistant_detector import AIAssistantDetector, DetectionState

    detector = AIAssistantDetector()
    report = detector.detect(events, session_id="sess-123")

    print(report.overall_state)   # DETECTED | SUSPECTED | NOT_DETECTED | UNOBSERVABLE
    print(report.summary)
    print(report.limitation_notice)
"""

from mcp.detectors.ai_assistant_detector.detector import (
    AIAssistantDetector,
    DetectionState,
    DetectionReport,
    AssistantDetectionResult,
)
from mcp.detectors.ai_assistant_detector.registry import (
    REGISTRY,
    get_all_domains,
    find_by_domain,
    is_monitored_domain,
)

__all__ = [
    "AIAssistantDetector",
    "DetectionState",
    "DetectionReport",
    "AssistantDetectionResult",
    "REGISTRY",
    "get_all_domains",
    "find_by_domain",
    "is_monitored_domain",
]
