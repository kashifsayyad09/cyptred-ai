# AI Exam Guardian — Browser Extension

Manifest V3 Chrome/Edge extension for exam integrity telemetry.

## Permissions

| Permission | Reason |
|-----------|--------|
| `activeTab` | Detect tab switches during exam |
| `storage` | Store active exam session state |

## What is collected

Only during an active exam session:
- Window focus/blur events
- Tab switch signals
- Copy/paste events
- Fullscreen exit events
- Visibility change events
- Common keyboard shortcut signals

## What is NOT collected
- Passwords
- Unrelated browsing history
- Private messages
- Any data outside an active exam session

## Installation (development)

1. Open Chrome/Edge → Extensions → Enable Developer Mode
2. Click "Load unpacked"
3. Select this `extension/` folder

## Build (Phase 3)

Full extension build tooling added in Phase 3.
