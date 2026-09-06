'use strict';

/**
 * AI Exam Guardian — Popup Script
 *
 * Queries the background service worker for current session state
 * and renders it in the popup UI.
 */

const statusDot  = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const detailsCard  = document.getElementById('detailsCard');
const riskCard     = document.getElementById('riskCard');
const sessionIdEl  = document.getElementById('sessionId');
const bufferedEl   = document.getElementById('bufferedCount');
const riskBadgeEl  = document.getElementById('riskBadge');

function setActive(session, buffered) {
  statusDot.className  = 'status__dot status__dot--active';
  statusText.textContent = 'Exam in progress';

  detailsCard.classList.remove('hidden');
  sessionIdEl.textContent = session.sessionId || '—';
  bufferedEl.textContent  = buffered ?? 0;

  riskCard.classList.remove('hidden');
  // Risk level fetched separately if available; default until fetched
  setRiskBadge('—');
}

function setIdle() {
  statusDot.className  = 'status__dot status__dot--idle';
  statusText.textContent = 'No active exam';
  detailsCard.classList.add('hidden');
  riskCard.classList.add('hidden');
}

function setRiskBadge(level) {
  riskBadgeEl.textContent  = level.replace(/_/g, ' ');
  riskBadgeEl.className    = `risk-badge risk-badge--${level}`;
}

// Query background SW for status
chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
  if (chrome.runtime.lastError || !response) {
    setIdle();
    return;
  }
  if (response.session) {
    setActive(response.session, response.buffered);

    // Attempt to show latest risk level
    chrome.storage.local.get(['lastRiskLevel'], (res) => {
      if (res.lastRiskLevel) setRiskBadge(res.lastRiskLevel);
    });
  } else {
    setIdle();
  }
});
