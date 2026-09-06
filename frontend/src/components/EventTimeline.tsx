/**
 * EventTimeline — renders the ordered evidence timeline for a session.
 * Each event row shows: timestamp, event type, severity indicator, score.
 */

import React from 'react';
import type { TimelineEvent } from '../types';

const SEVERITY_COLOR: Record<string, string> = {
  low:      '#6b7280',
  medium:   '#f59e0b',
  high:     '#f97316',
  critical: '#ef4444',
};

const EVENT_LABELS: Record<string, string> = {
  FOCUS_LOSS:           'Focus lost',
  FOCUS_GAIN:           'Focus returned',
  TAB_SWITCH:           'Tab switched',
  COPY:                 'Copy event',
  PASTE:                'Paste event',
  FULLSCREEN_EXIT:      'Fullscreen exited',
  SUSPICIOUS_NAVIGATION:'Navigation signal',
  AI_ASSISTANT_SIGNAL:  'AI assistant signal',
  KEYBOARD_SHORTCUT:    'Keyboard shortcut',
  DEVTOOLS_OPEN:        'DevTools signal',
  REPEATED_VIOLATIONS:  'Repeated violation',
  SUSPICIOUS_SEQUENCE:  'Suspicious sequence',
  EXAM_START:           'Exam started',
  EXAM_END:             'Exam ended',
};

interface Props {
  events: TimelineEvent[];
}

const EventTimeline: React.FC<Props> = ({ events }) => {
  if (events.length === 0) {
    return (
      <div style={{ color: '#6b7280', padding: '1.5rem', textAlign: 'center', fontSize: '14px' }}>
        No events recorded for this session.
      </div>
    );
  }

  return (
    <div style={{ fontFamily: 'inherit' }}>
      {events.map((ev, idx) => {
        const color = SEVERITY_COLOR[ev.severity] ?? '#6b7280';
        const label = EVENT_LABELS[ev.event_type] ?? ev.event_type;
        const meta  = ev.metadata ?? {};
        const url   = meta.url as string | undefined;
        const pasteLen = meta.paste_length as number | undefined;

        return (
          <div
            key={ev.id ?? idx}
            style={{
              display: 'grid',
              gridTemplateColumns: '160px 1fr 60px',
              gap: '0.5rem',
              padding: '10px 16px',
              borderBottom: '1px solid #1f2937',
              alignItems: 'start',
              background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
            }}
          >
            {/* Timestamp */}
            <span style={{ color: '#6b7280', fontSize: '12px', fontFamily: 'monospace', paddingTop: 2 }}>
              {ev.occurred_at || '—'}
            </span>

            {/* Event info */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: color, flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: '13px', fontWeight: 500, color: '#f3f4f6' }}>
                  {label}
                </span>
              </div>
              {url && (
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: 3, marginLeft: 16 }}>
                  url: {url}
                </div>
              )}
              {pasteLen !== undefined && (
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: 3, marginLeft: 16 }}>
                  {pasteLen} characters pasted
                </div>
              )}
              {ev.rule && (
                <div style={{ fontSize: '11px', color: '#6366f1', marginTop: 3, marginLeft: 16 }}>
                  rule: {ev.rule}
                </div>
              )}
            </div>

            {/* Score */}
            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: ev.score_contribution > 0 ? color : '#4b5563',
                textAlign: 'right',
              }}
            >
              {ev.score_contribution > 0 ? `+${ev.score_contribution}` : '—'}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default EventTimeline;
