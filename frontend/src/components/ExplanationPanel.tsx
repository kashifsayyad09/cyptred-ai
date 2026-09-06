/**
 * ExplanationPanel — displays the AI-generated incident explanation.
 *
 * Distinguishes:
 *   - OBSERVED EVIDENCE (from MCP deterministic rules)
 *   - POLICY INTERPRETATION (from RAG retrieved policy)
 *   - AI INFERENCE (from Groq/NVIDIA)
 *
 * Always shows the teacher disclaimer.
 * Shows provider, fallback status, and degraded state clearly.
 */

import React, { useState } from 'react';
import type { ExplanationResponse } from '../types';

interface Props {
  explanation: ExplanationResponse | null;
  loading: boolean;
  onRequest: () => void;
  disabled?: boolean;
}

const Label: React.FC<{ text: string; color: string }> = ({ text, color }) => (
  <span
    style={{
      display: 'inline-block',
      fontSize: '10px',
      fontWeight: 700,
      letterSpacing: '0.08em',
      color,
      background: `${color}18`,
      border: `1px solid ${color}40`,
      borderRadius: '4px',
      padding: '1px 7px',
      marginBottom: '6px',
    }}
  >
    {text}
  </span>
);

/** Split explanation text into labelled sections for rendering */
function splitSections(text: string): { label: string; content: string; color: string }[] {
  const sections: { label: string; content: string; color: string }[] = [];
  const labelMap: [RegExp, string, string][] = [
    [/\[OBSERVED EVIDENCE\]/i,       'OBSERVED EVIDENCE',       '#10b981'],
    [/\[POLICY INTERPRETATION\]/i,   'POLICY INTERPRETATION',   '#6366f1'],
    [/\[AI INFERENCE\]/i,            'AI INFERENCE',             '#f59e0b'],
  ];

  let remaining = text;

  // Simple section splitter: find label markers and cut
  const allMarkers: { idx: number; label: string; color: string }[] = [];
  for (const [rx, lbl, clr] of labelMap) {
    let m: RegExpExecArray | null;
    const rxG = new RegExp(rx.source, 'gi');
    while ((m = rxG.exec(remaining)) !== null) {
      allMarkers.push({ idx: m.index, label: lbl, color: clr });
    }
  }
  allMarkers.sort((a, b) => a.idx - b.idx);

  if (allMarkers.length === 0) {
    return [{ label: '', content: text, color: '#9ca3af' }];
  }

  // Text before first marker
  if (allMarkers[0].idx > 0) {
    sections.push({ label: '', content: remaining.slice(0, allMarkers[0].idx).trim(), color: '#9ca3af' });
  }

  for (let i = 0; i < allMarkers.length; i++) {
    const start = allMarkers[i].idx;
    const end   = allMarkers[i + 1]?.idx ?? remaining.length;
    const raw   = remaining.slice(start, end);
    // Remove the marker itself
    const content = raw.replace(/\[[A-Z ]+\]/i, '').trim();
    sections.push({ label: allMarkers[i].label, content, color: allMarkers[i].color });
  }

  return sections;
}

const ExplanationPanel: React.FC<Props> = ({ explanation, loading, onRequest, disabled }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div
      style={{
        background: '#111827',
        border: '1px solid #1f2937',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: '1px solid #1f2937',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(e => !e)}
      >
        <span style={{ fontWeight: 600, fontSize: '14px', color: '#f3f4f6' }}>
          AI Explanation
        </span>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {explanation && (
            <span
              style={{
                fontSize: '11px',
                color: explanation.is_fallback ? '#f59e0b' : '#10b981',
                background: explanation.is_fallback ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
                border: `1px solid ${explanation.is_fallback ? '#f59e0b40' : '#10b98140'}`,
                borderRadius: '4px',
                padding: '1px 7px',
              }}
            >
              {explanation.provider.toUpperCase()}
              {explanation.is_fallback ? ' (fallback)' : ''}
            </span>
          )}
          {explanation?.degraded && (
            <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 600 }}>DEGRADED</span>
          )}
          <span style={{ color: '#6b7280', fontSize: '12px' }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ padding: '16px' }}>
          {/* Request button */}
          {!explanation && !loading && (
            <button
              onClick={onRequest}
              disabled={disabled}
              style={{
                background: disabled ? '#374151' : '#3b82f6',
                color: disabled ? '#6b7280' : '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 18px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: disabled ? 'not-allowed' : 'pointer',
                width: '100%',
              }}
            >
              Generate AI Explanation
            </button>
          )}

          {/* Loading */}
          {loading && (
            <div style={{ color: '#9ca3af', fontSize: '13px', textAlign: 'center', padding: '1rem' }}>
              Generating explanation...
            </div>
          )}

          {/* Explanation content */}
          {explanation && !loading && (
            <div>
              {/* Integrity indicators */}
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  flexWrap: 'wrap',
                  marginBottom: '14px',
                  paddingBottom: '12px',
                  borderBottom: '1px solid #1f2937',
                }}
              >
                <IntegrityTag ok={explanation.has_evidence_label} label="Evidence Labelled" />
                <IntegrityTag ok={explanation.has_policy_label}   label="Policy Labelled" />
                <IntegrityTag ok={explanation.has_inference_label} label="Inference Labelled" />
                <IntegrityTag ok={explanation.has_disclaimer}     label="Disclaimer Present" />
                <IntegrityTag ok={explanation.mcp_summary_available} label="MCP Evidence" />
                <IntegrityTag ok={explanation.rag_policy_available}  label="RAG Policy" />
              </div>

              {/* Sectioned explanation */}
              {splitSections(explanation.explanation).map((sec, i) => (
                <div key={i} style={{ marginBottom: '14px' }}>
                  {sec.label && <Label text={sec.label} color={sec.color} />}
                  <p
                    style={{
                      fontSize: '13px',
                      lineHeight: 1.7,
                      color: '#d1d5db',
                      whiteSpace: 'pre-wrap',
                      margin: 0,
                    }}
                  >
                    {sec.content}
                  </p>
                </div>
              ))}

              {/* Teacher disclaimer */}
              <div
                style={{
                  marginTop: '14px',
                  paddingTop: '12px',
                  borderTop: '1px solid #1f2937',
                  fontSize: '12px',
                  color: '#6b7280',
                  fontStyle: 'italic',
                }}
              >
                {explanation.teacher_disclaimer}
              </div>

              {/* Latency */}
              <div style={{ marginTop: 8, fontSize: '11px', color: '#374151' }}>
                Generated in {explanation.latency_ms}ms
              </div>

              {/* Re-generate */}
              <button
                onClick={onRequest}
                disabled={disabled}
                style={{
                  marginTop: '12px',
                  background: 'transparent',
                  color: '#6b7280',
                  border: '1px solid #374151',
                  borderRadius: '5px',
                  padding: '5px 14px',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                Regenerate
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const IntegrityTag: React.FC<{ ok: boolean; label: string }> = ({ ok, label }) => (
  <span
    style={{
      fontSize: '10px',
      fontWeight: 600,
      color: ok ? '#10b981' : '#6b7280',
      background: ok ? 'rgba(16,185,129,0.08)' : 'rgba(107,114,128,0.08)',
      border: `1px solid ${ok ? '#10b98130' : '#37415130'}`,
      borderRadius: '4px',
      padding: '1px 7px',
    }}
  >
    {ok ? '✓' : '—'} {label}
  </span>
);

export default ExplanationPanel;
