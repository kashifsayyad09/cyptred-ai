/**
 * AI Exam Guardian — Extension Constants
 * Single source of truth for event types, storage keys, and config defaults.
 */

export const EVENT_TYPES = Object.freeze({
  // Tab / window focus
  TAB_SWITCH:        'TAB_SWITCH',
  TAB_HIDDEN:        'TAB_HIDDEN',
  TAB_VISIBLE:       'TAB_VISIBLE',
  FOCUS_LOSS:        'FOCUS_LOSS',
  FOCUS_REGAIN:      'FOCUS_REGAIN',
  WINDOW_BLUR:       'WINDOW_BLUR',
  WINDOW_FOCUS:      'WINDOW_FOCUS',

  // Clipboard
  COPY:              'COPY',
  PASTE:             'PASTE',

  // Fullscreen
  FULLSCREEN_ENTER:  'FULLSCREEN_ENTER',
  FULLSCREEN_EXIT:   'FULLSCREEN_EXIT',

  // Keyboard signals
  KEYBOARD_SHORTCUT: 'KEYBOARD_SHORTCUT',
  DEVTOOLS_SHORTCUT: 'DEVTOOLS_SHORTCUT',

  // Navigation
  NAVIGATION:        'NAVIGATION',

  // Session lifecycle
  EXAM_STARTED:      'EXAM_STARTED',
  EXAM_ENDED:        'EXAM_ENDED',
});

export const STORAGE_KEYS = Object.freeze({
  SESSION:    'examSession',
  API_BASE:   'apiBaseUrl',
  EVENT_BUF:  'eventBuffer',
  CONSENT:    'consentGiven',
});

export const DEFAULTS = Object.freeze({
  API_BASE:         'http://localhost:8000',
  FLUSH_INTERVAL_S: 5,      // seconds between event flushes
  MAX_BUFFER:       200,    // max events to buffer locally
  RETRY_LIMIT:      3,
  RETRY_DELAY_MS:   1000,
});

/** Keyboard combos treated as suspicious signals */
export const SUSPICIOUS_COMBOS = [
  { ctrl: true,  shift: true, key: 'I' },   // DevTools
  { ctrl: true,  shift: true, key: 'J' },   // DevTools console
  { ctrl: true,  shift: true, key: 'C' },   // DevTools inspect
  { key: 'F12' },
  { ctrl: true,  key: 'Tab' },              // tab cycling
  { alt: true,   key: 'Tab' },              // OS-level alt-tab (where catchable)
];
