"""
Detection signals — individual signal extractors used by the detector.

Each signal returns a SignalResult indicating whether a specific
observable indicator was present, with a confidence score.

Signals are combined by the detector — no single signal is conclusive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp.detectors.ai_assistant_detector.registry import (
    find_by_domain, is_monitored_domain, AssistantEntry,
)


@dataclass
class SignalResult:
    signal_name: str
    triggered: bool
    confidence: float      # 0.0–1.0
    assistant: str | None  # name if identifiable
    domain: str | None
    description: str
    metadata: dict[str, Any]


# ── Signal 1: Direct domain navigation ───────────────────────────────────────

def signal_domain_navigation(events: list[dict]) -> list[SignalResult]:
    """
    Check navigation events for known AI assistant domains.
    Covers: tab URL changes, navigation events, window.location signals.
    """
    results = []
    nav_types = {"TAB_SWITCH", "NAVIGATION", "SUSPICIOUS_NAVIGATION", "TAB_HIDDEN"}

    for ev in events:
        if ev.get("event_type") not in nav_types:
            continue
        meta = ev.get("metadata") or {}
        url = meta.get("toUrl") or meta.get("url") or ""
        domain = _extract_domain(url)
        if not domain:
            continue
        entry = find_by_domain(domain)
        if entry:
            results.append(SignalResult(
                signal_name="domain_navigation",
                triggered=True,
                confidence=0.90,
                assistant=entry.name,
                domain=domain,
                description=f"Navigation to {entry.name} domain: {domain}",
                metadata={"url": url, "event_type": ev.get("event_type"), "ts": ev.get("occurred_at")},
            ))
    return results


# ── Signal 2: Copy→paste sequence after focus loss ───────────────────────────

def signal_focus_copy_paste_sequence(events: list[dict]) -> list[SignalResult]:
    """
    Detect focus loss → (optional external nav) → copy → paste sequences.
    This pattern is the primary behavioral indicator for tools like ParakeetAI
    that are specifically designed to avoid URL-based detection.
    """
    from datetime import datetime, timedelta, timezone

    WINDOW_S = 120  # 2-minute window for the sequence

    sorted_events = sorted(events, key=lambda e: e.get("occurred_at", ""))
    types = [e.get("event_type", "") for e in sorted_events]
    timestamps = [e.get("occurred_at", "") for e in sorted_events]

    # Look for: FOCUS_LOSS/TAB_HIDDEN → ... → COPY/PASTE within window
    results = []
    for i, etype in enumerate(types):
        if etype not in ("FOCUS_LOSS", "TAB_HIDDEN", "WINDOW_BLUR"):
            continue
        focus_ts = _parse_ts(timestamps[i])
        if focus_ts is None:
            continue

        # Look for copy+paste within window after focus loss
        has_copy  = False
        has_paste = False
        paste_len = 0

        for j in range(i + 1, len(types)):
            ev_ts = _parse_ts(timestamps[j])
            if ev_ts and (ev_ts - focus_ts) > timedelta(seconds=WINDOW_S):
                break
            if types[j] == "COPY":
                has_copy = True
            if types[j] == "PASTE":
                has_paste = True
                paste_len = (sorted_events[j].get("metadata") or {}).get("pasteLength", 0)

        if has_paste:
            # Paste after focus loss is always suspicious
            confidence = 0.55
            if has_copy:
                confidence = 0.70   # copy + paste after focus loss
            if paste_len > 100:
                confidence += 0.10  # large paste increases confidence
            confidence = min(confidence, 0.85)

            results.append(SignalResult(
                signal_name="focus_copy_paste_sequence",
                triggered=True,
                confidence=confidence,
                assistant=None,  # cannot identify specific tool from behavior alone
                domain=None,
                description=(
                    "Focus loss followed by paste activity — "
                    "behavioral pattern consistent with AI-assisted answer insertion. "
                    "Cannot identify specific tool from behavior alone."
                ),
                metadata={
                    "has_copy": has_copy, "has_paste": has_paste,
                    "paste_length": paste_len, "focus_event_ts": timestamps[i],
                },
            ))
    return results


# ── Signal 3: Rapid answer insertion ─────────────────────────────────────────

def signal_rapid_large_paste(events: list[dict]) -> list[SignalResult]:
    """
    Large paste events (>150 chars) are unusual during normal exam writing.
    Combined with navigation, this is a strong behavioral signal.
    """
    results = []
    for ev in events:
        if ev.get("event_type") != "PASTE":
            continue
        paste_len = (ev.get("metadata") or {}).get("pasteLength", 0)
        if paste_len >= 150:
            confidence = min(0.50 + (paste_len / 2000), 0.80)
            results.append(SignalResult(
                signal_name="rapid_large_paste",
                triggered=True,
                confidence=confidence,
                assistant=None,
                domain=None,
                description=(
                    f"Large paste detected ({paste_len} chars). "
                    "Unusually large paste during exam — warrants review."
                ),
                metadata={"paste_length": paste_len, "ts": ev.get("occurred_at")},
            ))
    return results


# ── Signal 4: Repeated external navigation ────────────────────────────────────

def signal_repeated_navigation(events: list[dict]) -> list[SignalResult]:
    """
    Multiple external navigation events during an exam session.
    """
    nav_types = {"TAB_SWITCH", "NAVIGATION", "SUSPICIOUS_NAVIGATION"}
    nav_events = [e for e in events if e.get("event_type") in nav_types]
    count = len(nav_events)

    if count >= 3:
        return [SignalResult(
            signal_name="repeated_navigation",
            triggered=True,
            confidence=min(0.40 + count * 0.05, 0.75),
            assistant=None,
            domain=None,
            description=f"Student left exam {count} times — repeated external navigation.",
            metadata={"count": count},
        )]
    return []


# ── Signal 5: Keyboard shortcut patterns ────────────────────────────────────

def signal_keyboard_pattern(events: list[dict]) -> list[SignalResult]:
    """
    Common keyboard shortcuts associated with AI assistant activation.
    Limited confidence — shortcuts have many legitimate uses.
    """
    results = []
    for ev in events:
        if ev.get("event_type") not in ("KEYBOARD_SHORTCUT", "DEVTOOLS_SHORTCUT"):
            continue
        meta = ev.get("metadata") or {}
        combo = meta.get("combo", "")
        key   = meta.get("key", "")
        # Flag suspicious combos only
        if key in ("F12",) or combo in ("ctrl+tab", "alt+tab"):
            results.append(SignalResult(
                signal_name="keyboard_pattern",
                triggered=True,
                confidence=0.30,  # low confidence — many legitimate uses
                assistant=None,
                domain=None,
                description=f"Suspicious keyboard shortcut: {combo or key}",
                metadata=meta,
            ))
    return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    """Extract hostname from a URL string."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else "https://" + url)
        return parsed.hostname or ""
    except Exception:
        return ""


def _parse_ts(ts_str: str):
    from datetime import datetime
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None
