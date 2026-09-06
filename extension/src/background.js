/**
 * AI Exam Guardian — Background Service Worker (Manifest V3)
 *
 * Responsibilities:
 *  - Manage active exam session state
 *  - Receive telemetry from content script
 *  - Buffer events locally and flush to FastAPI on interval
 *  - Detect tab-switch via chrome.tabs.onActivated
 *  - Expose session status to popup
 *
 * PRIVACY:
 *  - Only collects telemetry when an exam session is explicitly active
 *  - Never collects passwords, unrelated history, private messages, or
 *    any data outside the scope of the active exam session
 *  - Students must give explicit consent before a session is started
 */

'use strict';

import { EVENT_TYPES, STORAGE_KEYS, DEFAULTS } from './constants.js';
import { flushEvents, endSessionOnBackend } from './api.js';

// ── In-memory session state (recreated from storage on SW restart) ────────────
let session = null;   // { sessionId, token, examId, apiBase }
let eventBuffer = []; // local buffer before flush
let examTabId = null; // the tab that started the exam

// ── Restore state after service worker restart ────────────────────────────────
chrome.storage.local.get([STORAGE_KEYS.SESSION, STORAGE_KEYS.EVENT_BUF], (res) => {
  if (res[STORAGE_KEYS.SESSION]) {
    session = res[STORAGE_KEYS.SESSION];
  }
  if (res[STORAGE_KEYS.EVENT_BUF]) {
    eventBuffer = res[STORAGE_KEYS.EVENT_BUF];
  }
});

// ── Periodic flush alarm ──────────────────────────────────────────────────────
chrome.alarms.create('flush', { periodInMinutes: DEFAULTS.FLUSH_INTERVAL_S / 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'flush') flushBuffer();
});

// ── Message bus ───────────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {
    case 'EXAM_START':
      handleExamStart(msg.payload, sender.tab?.id);
      sendResponse({ ok: true });
      break;

    case 'EXAM_END':
      handleExamEnd();
      sendResponse({ ok: true });
      break;

    case 'TELEMETRY':
      if (session) bufferEvent(buildEvent(msg.eventType, msg.metadata));
      sendResponse({ ok: true });
      break;

    case 'GET_STATUS':
      sendResponse({ session, buffered: eventBuffer.length });
      break;

    default:
      sendResponse({ ok: false, error: 'Unknown message type' });
  }
  return true; // keep channel open for async
});

// ── Tab activation ────────────────────────────────────────────────────────────
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  if (!session) return;
  // Only flag if student switched AWAY from the exam tab
  if (examTabId && tabId !== examTabId) {
    try {
      const tab = await chrome.tabs.get(tabId);
      bufferEvent(buildEvent(EVENT_TYPES.TAB_SWITCH, {
        toUrl: sanitizeUrl(tab.url || ''),
        fromTabId: examTabId,
        toTabId: tabId,
      }));
    } catch {
      bufferEvent(buildEvent(EVENT_TYPES.TAB_SWITCH, {}));
    }
  }
  examTabId = tabId;
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildEvent(eventType, metadata = {}) {
  return {
    session_id:   session.sessionId,
    event_type:   eventType,
    occurred_at:  new Date().toISOString(),
    source:       'extension',
    metadata,
  };
}

function bufferEvent(event) {
  eventBuffer.push(event);
  // Cap buffer to avoid unbounded growth
  if (eventBuffer.length > DEFAULTS.MAX_BUFFER) {
    eventBuffer = eventBuffer.slice(-DEFAULTS.MAX_BUFFER);
  }
  persistBuffer();
}

function persistBuffer() {
  chrome.storage.local.set({ [STORAGE_KEYS.EVENT_BUF]: eventBuffer });
}

async function flushBuffer() {
  if (!session || !eventBuffer.length) return;
  const toFlush = [...eventBuffer];
  const ok = await flushEvents(session.apiBase, session.token, toFlush);
  if (ok) {
    // Remove successfully sent events
    eventBuffer = eventBuffer.slice(toFlush.length);
    persistBuffer();
  }
}

function handleExamStart({ sessionId, token, examId, apiBase }, tabId) {
  session = {
    sessionId,
    token,
    examId,
    apiBase: apiBase || DEFAULTS.API_BASE,
  };
  examTabId = tabId || null;
  eventBuffer = [];
  chrome.storage.local.set({
    [STORAGE_KEYS.SESSION]: session,
    [STORAGE_KEYS.EVENT_BUF]: [],
  });
  bufferEvent(buildEvent(EVENT_TYPES.EXAM_STARTED, { examId }));
  console.log('[ExamGuardian] Exam session started:', sessionId);
}

async function handleExamEnd() {
  if (session) {
    bufferEvent(buildEvent(EVENT_TYPES.EXAM_ENDED, {}));
    await flushBuffer(); // final flush before clearing
    await endSessionOnBackend(session.apiBase, session.token, session.sessionId);
  }
  session = null;
  examTabId = null;
  eventBuffer = [];
  chrome.storage.local.remove([STORAGE_KEYS.SESSION, STORAGE_KEYS.EVENT_BUF]);
  console.log('[ExamGuardian] Exam session ended.');
}

/**
 * Strip query params and fragments from URLs before logging —
 * we only need the hostname for navigation signals.
 */
function sanitizeUrl(url) {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.hostname}${u.pathname}`;
  } catch {
    return 'unknown';
  }
}
