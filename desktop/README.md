# AI Exam Guardian — Desktop App (Electron)

> **Status:** Placeholder — Full implementation is a future/advanced component.

## Overview

The Electron desktop wrapper provides an optional stronger monitoring environment. Desktop-level monitoring can capture signals not available to browser extensions, with appropriate user consent.

## Platform Requirements

### Windows
- Requires code signing certificate for production distribution
- NSIS installer target
- Unsigned builds trigger Windows SmartScreen warnings

### macOS
- Requires Apple Developer ID for production distribution
- Notarization required for Gatekeeper bypass
- DMG target

## Security Notes

- `nodeIntegration` is disabled — renderer process has no Node.js access
- `contextIsolation` is enabled — preload script uses `contextBridge`
- No AI API keys are ever loaded in the renderer process

## Build

```bash
# Windows
npm run build:win

# macOS
npm run build:mac
```

## Status

Full desktop implementation planned as a post-MVP enhancement.
