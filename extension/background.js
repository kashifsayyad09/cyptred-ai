/**
 * AI Exam Guardian — Background Service Worker (Manifest V3)
 *
 * Collects only permitted exam-integrity telemetry.
 * No passwords, no unrelated browsing history, no private messages.
 */

// Active exam session state
let examSession = null;
let apiBaseUrl = 'http://localhost:8000';

// Load config from storage
chrome.storage.local.get(['apiBaseUrl'], (result) => {
  if (result.apiBaseUrl) apiBaseUrl = result.apiBaseUrl;
});

/**
 * Send a telemetry event to the backend.
 * Called only when an active exam session exists.
 */
async function sendEvent(eventType, metadata = {}) {
  if (!examSession) return;

  const payload = {
    session_id: examSession.sessionId,
    event_type: eventType,
    timestamp: new Date().toISOString(),
    metadata,
  };

  try {
    await fetch(`${apiBaseUrl}/api/v1/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${examSession.token}`,
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    // Log locally; do not crash the service worker
    console.warn('[ExamGuardian] Failed to send event:', eventType, err.message);
  }
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case 'EXAM_START':
      examSession = {
        sessionId: message.sessionId,
        token: message.token,
        examId: message.examId,
      };
      sendResponse({ ok: true });
      break;

    case 'EXAM_END':
      examSession = null;
      sendResponse({ ok: true });
      break;

    case 'TELEMETRY_EVENT':
      sendEvent(message.eventType, message.metadata);
      sendResponse({ ok: true });
      break;

    default:
      sendResponse({ ok: false, error: 'Unknown message type' });
  }
  return true; // Keep message channel open for async
});

// Tab activation change
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  if (!examSession) return;
  const tab = await chrome.tabs.get(activeInfo.tabId);
  await sendEvent('TAB_SWITCH', { tabId: activeInfo.tabId, url: tab.url || 'unknown' });
});
