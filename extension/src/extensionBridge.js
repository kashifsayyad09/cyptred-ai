/**
 * AI Exam Guardian — Exam Page Bridge
 *
 * Used by the React exam page to start and end an exam session.
 * Posts window messages that the content script picks up and forwards
 * to the background service worker.
 *
 * Usage (in React ExamPage component):
 *
 *   import { startExamSession, endExamSession } from './extensionBridge';
 *
 *   // When exam begins:
 *   startExamSession({ sessionId, token, examId, apiBase });
 *
 *   // When exam ends:
 *   endExamSession();
 */

'use strict';

/**
 * Signal the extension to start monitoring.
 * @param {{ sessionId: string, token: string, examId: string, apiBase?: string }} params
 */
export function startExamSession({ sessionId, token, examId, apiBase }) {
  window.postMessage({
    type: 'EXAM_GUARDIAN_START',
    sessionId,
    token,
    examId,
    apiBase: apiBase || '/api/v1',
  }, window.location.origin);
}

/**
 * Signal the extension to end monitoring and flush final events.
 */
export function endExamSession() {
  window.postMessage({ type: 'EXAM_GUARDIAN_END' }, window.location.origin);
}

/**
 * Check whether the extension is installed and responding.
 * Resolves to true/false within 500ms.
 * @returns {Promise<boolean>}
 */
export function isExtensionPresent() {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(false), 500);
    try {
      // eslint-disable-next-line no-undef
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id) {
        clearTimeout(timeout);
        resolve(true);
      } else {
        clearTimeout(timeout);
        resolve(false);
      }
    } catch {
      clearTimeout(timeout);
      resolve(false);
    }
  });
}
