/**
 * AI Exam Guardian — Content Script
 *
 * Runs on exam pages only (per manifest content_scripts matches).
 * Captures permitted exam-integrity telemetry and forwards to background SW.
 *
 * WHAT IS COLLECTED (only during active exam):
 *   - Window/document focus and blur
 *   - Visibility changes (tab switch)
 *   - Fullscreen enter/exit
 *   - Copy and paste (paste length only — never clipboard text)
 *   - DevTools / tab-switch keyboard shortcuts
 *
 * WHAT IS NEVER COLLECTED:
 *   - Clipboard content / text
 *   - Keystrokes / typed content
 *   - Passwords
 *   - Unrelated page content
 *   - Any data outside an active exam session
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
let examActive = false;

// Sync state from storage
chrome.storage.local.get(['examSession'], (res) => {
  examActive = !!res.examSession;
});

chrome.storage.onChanged.addListener((changes) => {
  if ('examSession' in changes) {
    examActive = !!changes.examSession.newValue;
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function emit(eventType, metadata = {}) {
  if (!examActive) return;
  chrome.runtime.sendMessage({ type: 'TELEMETRY', eventType, metadata }, () => {
    // Silence "receiving end does not exist" when SW is sleeping
    void chrome.runtime.lastError;
  });
}

// ── Document visibility (tab hidden / visible) ────────────────────────────────
document.addEventListener('visibilitychange', () => {
  emit(document.hidden ? 'TAB_HIDDEN' : 'TAB_VISIBLE', {
    source: 'visibilitychange',
  });
});

// ── Window focus / blur ───────────────────────────────────────────────────────
window.addEventListener('blur', () => emit('WINDOW_BLUR', { source: 'window' }));
window.addEventListener('focus', () => emit('WINDOW_FOCUS', { source: 'window' }));

// ── Fullscreen ────────────────────────────────────────────────────────────────
document.addEventListener('fullscreenchange', () => {
  emit(document.fullscreenElement ? 'FULLSCREEN_ENTER' : 'FULLSCREEN_EXIT', {});
});

// ── Copy ──────────────────────────────────────────────────────────────────────
document.addEventListener('copy', () => emit('COPY', { source: 'document' }));

// ── Paste — record length only, NEVER the text content ───────────────────────
document.addEventListener('paste', (e) => {
  const pasteLength = e.clipboardData?.getData('text')?.length ?? 0;
  emit('PASTE', { pasteLength, source: 'document' });
});

// ── Keyboard signals ──────────────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (!examActive) return;

  // DevTools shortcuts
  if (
    e.key === 'F12' ||
    (e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key))
  ) {
    emit('DEVTOOLS_SHORTCUT', { key: e.key, ctrl: e.ctrlKey, shift: e.shiftKey });
    return;
  }

  // Tab-switch shortcuts
  if ((e.ctrlKey && e.key === 'Tab') || (e.altKey && e.key === 'Tab')) {
    emit('KEYBOARD_SHORTCUT', {
      key: e.key,
      ctrl: e.ctrlKey,
      alt: e.altKey,
      combo: e.ctrlKey ? 'ctrl+tab' : 'alt+tab',
    });
  }
});

// ── Exam lifecycle messages (from exam page JS) ───────────────────────────────
window.addEventListener('message', (e) => {
  if (e.origin !== window.location.origin) return;
  if (!e.data || typeof e.data !== 'object') return;

  if (e.data.type === 'EXAM_GUARDIAN_START') {
    const { sessionId, token, examId, apiBase } = e.data;
    chrome.runtime.sendMessage({
      type: 'EXAM_START',
      payload: { sessionId, token, examId, apiBase },
    });
  }

  if (e.data.type === 'EXAM_GUARDIAN_END') {
    chrome.runtime.sendMessage({ type: 'EXAM_END' });
  }
});

console.log('[ExamGuardian] Content script active on exam page.');
