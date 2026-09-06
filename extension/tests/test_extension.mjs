/**
 * AI Exam Guardian — Extension Unit Tests
 *
 * Tests run with Node.js (no browser required) against the pure-logic
 * modules. Browser API tests (chrome.*, DOM events) are integration
 * tests run manually in Chrome or via Playwright in Phase 12.
 */

'use strict';

// ── Import modules under test ─────────────────────────────────────────────────
// We test the pure-logic exports that have no browser dependencies.
import { EVENT_TYPES, STORAGE_KEYS, DEFAULTS, SUSPICIOUS_COMBOS } from '../src/constants.js';

// ── EVENT_TYPES ───────────────────────────────────────────────────────────────

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    return true;
  } catch (e) {
    console.error(`  ✗ ${name}\n    ${e.message}`);
    return false;
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
}

function assertEqual(a, b) {
  if (a !== b) throw new Error(`Expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
}

let passed = 0, failed = 0;

function run(name, fn) {
  if (test(name, fn)) passed++; else failed++;
}

console.log('\nAI Exam Guardian — Extension Unit Tests\n');

// ── Constants ─────────────────────────────────────────────────────────────────
console.log('EVENT_TYPES:');
run('contains TAB_SWITCH', () => assert(EVENT_TYPES.TAB_SWITCH === 'TAB_SWITCH'));
run('contains FOCUS_LOSS', () => assert(EVENT_TYPES.FOCUS_LOSS === 'FOCUS_LOSS'));
run('contains COPY',       () => assert(EVENT_TYPES.COPY === 'COPY'));
run('contains PASTE',      () => assert(EVENT_TYPES.PASTE === 'PASTE'));
run('contains FULLSCREEN_EXIT', () => assert(EVENT_TYPES.FULLSCREEN_EXIT === 'FULLSCREEN_EXIT'));
run('contains KEYBOARD_SHORTCUT', () => assert(EVENT_TYPES.KEYBOARD_SHORTCUT === 'KEYBOARD_SHORTCUT'));
run('contains DEVTOOLS_SHORTCUT', () => assert(EVENT_TYPES.DEVTOOLS_SHORTCUT === 'DEVTOOLS_SHORTCUT'));
run('contains NAVIGATION', () => assert(EVENT_TYPES.NAVIGATION === 'NAVIGATION'));
run('contains EXAM_STARTED', () => assert(EVENT_TYPES.EXAM_STARTED === 'EXAM_STARTED'));
run('contains EXAM_ENDED',   () => assert(EVENT_TYPES.EXAM_ENDED === 'EXAM_ENDED'));
run('is frozen (immutable)', () => {
  try { EVENT_TYPES.FAKE = 'x'; } catch { /* strict mode throws */ }
  assert(!EVENT_TYPES.FAKE, 'EVENT_TYPES must be frozen');
});

console.log('\nSTORAGE_KEYS:');
run('SESSION key defined',   () => assert(STORAGE_KEYS.SESSION === 'examSession'));
run('API_BASE key defined',  () => assert(STORAGE_KEYS.API_BASE === 'apiBaseUrl'));
run('EVENT_BUF key defined', () => assert(STORAGE_KEYS.EVENT_BUF === 'eventBuffer'));
run('CONSENT key defined',   () => assert(STORAGE_KEYS.CONSENT === 'consentGiven'));

console.log('\nDEFAULTS:');
run('FLUSH_INTERVAL is positive', () => assert(DEFAULTS.FLUSH_INTERVAL_S > 0));
run('MAX_BUFFER is positive',     () => assert(DEFAULTS.MAX_BUFFER > 0));
run('API_BASE is localhost in dev', () => assert(DEFAULTS.API_BASE.includes('localhost')));
run('RETRY_LIMIT is positive',    () => assert(DEFAULTS.RETRY_LIMIT > 0));

console.log('\nSUSPICIOUS_COMBOS:');
run('is non-empty array', () => assert(Array.isArray(SUSPICIOUS_COMBOS) && SUSPICIOUS_COMBOS.length > 0));
run('includes F12',        () => assert(SUSPICIOUS_COMBOS.some(c => c.key === 'F12')));
run('includes ctrl+shift+I', () => assert(SUSPICIOUS_COMBOS.some(c => c.ctrl && c.shift && c.key === 'I')));
run('includes ctrl+Tab',   () => assert(SUSPICIOUS_COMBOS.some(c => c.ctrl && c.key === 'Tab')));

// ── Risk classification (mirrors backend logic) ───────────────────────────────
console.log('\nRisk classification:');

function classifyRisk(score) {
  if (score < 20) return 'NORMAL';
  if (score < 40) return 'MONITORING';
  if (score < 60) return 'ATTENTION';
  if (score < 80) return 'REVIEW_REQUIRED';
  return 'HIGH_PRIORITY_REVIEW';
}

const riskCases = [
  [0, 'NORMAL'], [19, 'NORMAL'],
  [20, 'MONITORING'], [39, 'MONITORING'],
  [40, 'ATTENTION'], [59, 'ATTENTION'],
  [60, 'REVIEW_REQUIRED'], [79, 'REVIEW_REQUIRED'],
  [80, 'HIGH_PRIORITY_REVIEW'], [100, 'HIGH_PRIORITY_REVIEW'],
];

riskCases.forEach(([score, expected]) => {
  run(`score ${score} → ${expected}`, () => assertEqual(classifyRisk(score), expected));
});

// ── URL sanitizer (inline test for the pattern in background.js) ──────────────
console.log('\nURL sanitization:');

function sanitizeUrl(url) {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.hostname}${u.pathname}`;
  } catch {
    return 'unknown';
  }
}

run('strips query params',  () => assertEqual(sanitizeUrl('https://example.com/path?q=secret'), 'https://example.com/path'));
run('strips fragment',      () => assertEqual(sanitizeUrl('https://example.com/page#section'), 'https://example.com/page'));
run('handles invalid URL',  () => assertEqual(sanitizeUrl('not-a-url'), 'unknown'));
run('keeps hostname+path',  () => assertEqual(sanitizeUrl('https://parakeet-ai.com/app'), 'https://parakeet-ai.com/app'));

// ── Summary ───────────────────────────────────────────────────────────────────
console.log(`\n${'─'.repeat(40)}`);
console.log(`Results: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
