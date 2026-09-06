"""Tools package."""
from mcp.tools.handlers import (
    check_focus_loss, check_tab_switch, check_copy, check_paste,
    check_navigation, check_fullscreen, check_keyboard_shortcuts,
    check_devtools_signal, check_ai_assistant_signal,
    detect_ai_assistants,
    correlate_behavior, calculate_risk,
    get_exam_rules, get_policy, get_student_timeline,
    create_incident_summary,
)

TOOL_REGISTRY = {
    "check_focus_loss":          check_focus_loss,
    "check_tab_switch":          check_tab_switch,
    "check_copy":                check_copy,
    "check_paste":               check_paste,
    "check_navigation":          check_navigation,
    "check_fullscreen":          check_fullscreen,
    "check_keyboard_shortcuts":  check_keyboard_shortcuts,
    "check_devtools_signal":     check_devtools_signal,
    "check_ai_assistant_signal": check_ai_assistant_signal,
    "detect_ai_assistants":      detect_ai_assistants,
    "correlate_behavior":        correlate_behavior,
    "calculate_risk":            calculate_risk,
    "get_exam_rules":            get_exam_rules,
    "get_policy":                get_policy,
    "get_student_timeline":      get_student_timeline,
    "create_incident_summary":   create_incident_summary,
}

__all__ = list(TOOL_REGISTRY.keys()) + ["TOOL_REGISTRY"]
