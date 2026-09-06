/**
 * AI Exam Guardian — API Client (extension-side)
 *
 * Sends telemetry events to the FastAPI backend.
 * All requests include the session JWT — never an AI provider key.
 */

import { DEFAULTS } from './constants.js';

/**
 * Send a batch of events to POST /api/v1/events.
 * Returns true on success, false on any failure (caller buffers for retry).
 *
 * @param {string} apiBase
 * @param {string} token
 * @param {Array<object>} events
 * @returns {Promise<boolean>}
 */
export async function flushEvents(apiBase, token, events) {
  if (!events.length) return true;

  for (const event of events) {
    try {
      const res = await fetch(`${apiBase}/api/v1/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(event),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) {
        console.warn('[ExamGuardian] Event rejected:', res.status, event.event_type);
      }
    } catch (err) {
      console.warn('[ExamGuardian] Network error flushing event:', err.message);
      return false;
    }
  }
  return true;
}

/**
 * Fetch the current risk score for a session.
 * @returns {Promise<object|null>}
 */
export async function fetchRisk(apiBase, token, sessionId) {
  try {
    const res = await fetch(`${apiBase}/api/v1/risk/${sessionId}/latest`, {
      headers: { 'Authorization': `Bearer ${token}` },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * End the exam session on the backend.
 * @returns {Promise<boolean>}
 */
export async function endSessionOnBackend(apiBase, token, sessionId) {
  try {
    const res = await fetch(`${apiBase}/api/v1/sessions/${sessionId}/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      signal: AbortSignal.timeout(8000),
    });
    return res.ok;
  } catch {
    return false;
  }
}
