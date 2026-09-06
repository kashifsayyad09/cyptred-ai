/**
 * AI Exam Guardian — Content Script
 *
 * Runs on exam pages only (per manifest content_scripts matches).
 * Captures permitted exam-integrity telemetry and forwards to background worker.
 */

(function () {
  'use strict';

  function sendTelemetry(eventType, metadata = {}) {
    chrome.runtime.sendMessage({
      type: 'TELEMETRY_EVENT',
      eventType,
      metadata,
    });
  }

  // Focus / blur
  window.addEventListener('blur', () => sendTelemetry('FOCUS_LOSS', { source: 'window_blur' }));
  window.addEventListener('focus', () => sendTelemetry('FOCUS_REGAIN', { source: 'window_focus' }));

  // Fullscreen change
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) {
      sendTelemetry('FULLSCREEN_EXIT', {});
    }
  });

  // Copy / paste
  document.addEventListener('copy', () => sendTelemetry('COPY', { source: 'document_copy' }));
  document.addEventListener('paste', () => sendTelemetry('PASTE', { source: 'document_paste' }));

  // Visibility change
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      sendTelemetry('TAB_HIDDEN', { source: 'visibilitychange' });
    } else {
      sendTelemetry('TAB_VISIBLE', { source: 'visibilitychange' });
    }
  });

  // Keyboard shortcut detection (common AI assistant shortcuts)
  document.addEventListener('keydown', (e) => {
    // Alt+Tab equivalent attempt, Ctrl+Tab
    if ((e.ctrlKey && e.key === 'Tab') || (e.altKey && e.key === 'Tab')) {
      sendTelemetry('KEYBOARD_SHORTCUT', { key: e.key, ctrl: e.ctrlKey, alt: e.altKey });
    }
  });

  console.log('[ExamGuardian] Content script active — monitoring exam integrity signals.');
})();
