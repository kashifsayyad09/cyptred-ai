/**
 * AI Exam Guardian — Exam Page ↔ Extension Bridge
 *
 * Posts window messages that the Manifest V3 content script picks up
 * and forwards to the background service worker.
 *
 * This file lives inside frontend/src/ (React build boundary).
 * The canonical source for the extension is extension/src/extensionBridge.js —
 * keep both files in sync if you change the message protocol.
 */

export interface ExamSessionParams {
  sessionId: string;
  token: string;
  examId: string;
  apiBase?: string;
}

/**
 * Signal the extension to start monitoring.
 */
export function startExamSession({ sessionId, token, examId, apiBase }: ExamSessionParams): void {
  window.postMessage(
    {
      type: 'EXAM_GUARDIAN_START',
      sessionId,
      token,
      examId,
      apiBase: apiBase ?? '/api/v1',
    },
    window.location.origin
  );
}

/**
 * Signal the extension to end monitoring and flush final events.
 */
export function endExamSession(): void {
  window.postMessage({ type: 'EXAM_GUARDIAN_END' }, window.location.origin);
}

/**
 * Check whether the extension is installed and responding.
 * Resolves to true within 500 ms if the extension is present, false otherwise.
 */
export function isExtensionPresent(): Promise<boolean> {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(false), 500);
    try {
      // chrome is defined only when the page runs inside a Chrome/Edge extension context
      // or on a page where the extension has injected a content script.
      const chromeRuntime = (window as any).chrome?.runtime;
      if (chromeRuntime?.id) {
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
