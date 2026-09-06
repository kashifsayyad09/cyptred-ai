/**
 * SessionDetailPage — full incident review for one exam session.
 *
 * Shows:
 *  - Session header: student, exam, risk badge, AI detection state
 *  - Risk score progress bar
 *  - Event count + timing summary
 *  - Evidence timeline (EventTimeline component)
 *  - AI Explanation panel (ExplanationPanel component)
 *  - Provider health panel
 *
 * Uses mock data for development when backend is unavailable.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { gsap } from 'gsap';
import RiskBadge from '../components/RiskBadge';
import EventTimeline from '../components/EventTimeline';
import ExplanationPanel from '../components/ExplanationPanel';
import {
  fetchSession,
  fetchSessionEvents,
  requestExplanation,
  fetchProviderHealth,
} from '../api/dashboard';
import type {
  ExamSession,
  TimelineEvent,
  ExplanationResponse,
  ProviderHealthStatus,
} from '../types';

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_SESSION: ExamSession = {
  id: 'sess-001',
  examId: 'exam-001',
  examTitle: 'Advanced Algorithms Midterm',
  studentId: 'stu-101',
  studentName: 'Student A',
  startedAt: '2025-01-15T10:31:04Z',
  riskScore: 85,
  riskLevel: 'HIGH_PRIORITY_REVIEW',
  aiDetectionState: 'DETECTED',
  eventCount: 14,
  status: 'flagged',
};

const MOCK_EVENTS: TimelineEvent[] = [
  {
    id: 'e1', sessionId: 'sess-001', occurred_at: '10:31:04', event_type: 'EXAM_START',
    source: 'extension', rule: null, severity: 'low', score_contribution: 0, confidence: 1, metadata: {},
  },
  {
    id: 'e2', sessionId: 'sess-001', occurred_at: '10:42:11', event_type: 'FOCUS_LOSS',
    source: 'extension', rule: 'focus_loss', severity: 'medium', score_contribution: 5, confidence: 0.9,
    metadata: {},
  },
  {
    id: 'e3', sessionId: 'sess-001', occurred_at: '10:42:18', event_type: 'SUSPICIOUS_NAVIGATION',
    source: 'extension', rule: 'suspicious_navigation', severity: 'high', score_contribution: 20, confidence: 0.85,
    metadata: { url: 'https://parakeet-ai.com' },
  },
  {
    id: 'e4', sessionId: 'sess-001', occurred_at: '10:42:41', event_type: 'FOCUS_GAIN',
    source: 'extension', rule: null, severity: 'low', score_contribution: 0, confidence: 0.9, metadata: {},
  },
  {
    id: 'e5', sessionId: 'sess-001', occurred_at: '10:42:45', event_type: 'COPY',
    source: 'extension', rule: 'copy_event', severity: 'medium', score_contribution: 15, confidence: 0.95,
    metadata: {},
  },
  {
    id: 'e6', sessionId: 'sess-001', occurred_at: '10:42:49', event_type: 'PASTE',
    source: 'extension', rule: 'paste_event', severity: 'high', score_contribution: 15, confidence: 0.95,
    metadata: { paste_length: 450 },
  },
  {
    id: 'e7', sessionId: 'sess-001', occurred_at: '10:43:02', event_type: 'AI_ASSISTANT_SIGNAL',
    source: 'mcp', rule: 'ai_assistant_detection', severity: 'critical', score_contribution: 25, confidence: 0.82,
    metadata: { assistant: 'ParakeetAI', detection_state: 'DETECTED' },
  },
];

// ── Risk score bar ────────────────────────────────────────────────────────────

const RISK_BAR_COLOR: Record<string, string> = {
  NORMAL:               '#10b981',
  MONITORING:           '#3b82f6',
  ATTENTION:            '#f59e0b',
  REVIEW_REQUIRED:      '#f97316',
  HIGH_PRIORITY_REVIEW: '#ef4444',
};

const RiskScoreBar: React.FC<{ score: number; level: string }> = ({ score, level }) => {
  const barRef = useRef<HTMLDivElement>(null);
  const color  = RISK_BAR_COLOR[level] ?? '#6b7280';

  useEffect(() => {
    if (!barRef.current) return;
    gsap.fromTo(barRef.current, { width: '0%' }, { width: `${score}%`, duration: 0.8, ease: 'power3.out' });
  }, [score]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Risk Score</span>
        <span style={{ fontSize: 20, fontWeight: 700, color }}>{score}</span>
      </div>
      <div
        style={{
          background: '#1f2937',
          borderRadius: 4,
          height: 8,
          overflow: 'hidden',
        }}
      >
        <div
          ref={barRef}
          style={{ height: '100%', background: color, borderRadius: 4, width: 0 }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 10, color: '#374151' }}>0</span>
        <span style={{ fontSize: 10, color: '#374151' }}>100</span>
      </div>
    </div>
  );
};

// ── Provider health indicator ─────────────────────────────────────────────────

const ProviderHealthPanel: React.FC<{ health: ProviderHealthStatus | null }> = ({ health }) => {
  if (!health) return null;
  const stateColor = (s: string) =>
    s === 'healthy' ? '#10b981' : s === 'degraded' ? '#f59e0b' : '#ef4444';

  return (
    <div
      style={{
        background: '#111827',
        border: '1px solid #1f2937',
        borderRadius: 8,
        padding: '14px 16px',
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', marginBottom: 10, letterSpacing: '0.05em' }}>
        AI PROVIDER STATUS
      </div>
      {['groq', 'nvidia'].map((p) => {
        const ph = (health as any)[p] as { state: string; consecutive_failures: number };
        return (
          <div key={p} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: '#9ca3af', textTransform: 'uppercase' }}>{p}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: stateColor(ph?.state) }}>
              {ph?.state ?? 'unknown'}
            </span>
          </div>
        );
      })}
      <div style={{ fontSize: 11, color: '#374151', marginTop: 6 }}>
        Primary: {health.active_primary.toUpperCase()}
      </div>
    </div>
  );
};

// ── Section card wrapper ──────────────────────────────────────────────────────

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div
    style={{
      background: '#111827',
      border: '1px solid #1f2937',
      borderRadius: 8,
      overflow: 'hidden',
      marginBottom: 16,
    }}
  >
    <div
      style={{
        padding: '10px 16px',
        borderBottom: '1px solid #1f2937',
        fontSize: 12,
        fontWeight: 700,
        color: '#6b7280',
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
      }}
    >
      {title}
    </div>
    {children}
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

const SessionDetailPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const headerRef = useRef<HTMLDivElement>(null);

  const [session,   setSession]   = useState<ExamSession | null>(null);
  const [events,    setEvents]    = useState<TimelineEvent[]>([]);
  const [health,    setHealth]    = useState<ProviderHealthStatus | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    Promise.all([
      fetchSession(sessionId).catch(() => MOCK_SESSION),
      fetchSessionEvents(sessionId).catch(() => MOCK_EVENTS),
      fetchProviderHealth().catch(() => null),
    ]).then(([sess, evts, ph]) => {
      if (cancelled) return;
      setSession(sess);
      setEvents(evts.length > 0 ? evts : MOCK_EVENTS);
      setHealth(ph);
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [sessionId]);

  // Animate header in
  useEffect(() => {
    if (headerRef.current && !loading) {
      gsap.fromTo(headerRef.current, { opacity: 0, y: -8 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' });
    }
  }, [loading]);

  const handleRequestExplanation = async () => {
    if (!session) return;
    setExplainLoading(true);
    try {
      const result = await requestExplanation({
        session_id:   session.id,
        exam_title:   session.examTitle,
        risk_score:   session.riskScore,
        risk_level:   session.riskLevel,
        events:       events as any,
      });
      setExplanation(result);
    } catch {
      // Degraded mock explanation when backend unavailable
      setExplanation({
        session_id:       session.id,
        explanation:
          `[OBSERVED EVIDENCE]\nRisk Score: ${session.riskScore}/100 — Level: ${session.riskLevel}\n` +
          `${events.length} events recorded including suspicious navigation and copy/paste sequences.\n\n` +
          `[POLICY INTERPRETATION]\nAI assistants are prohibited during closed-resource examinations.\n\n` +
          `[AI INFERENCE]\nThe combination of external navigation to a known AI-assistant domain followed by ` +
          `copy/paste events is consistent with AI assistant usage. This warrants teacher review.\n\n` +
          `The final determination belongs to the reviewing teacher.`,
        teacher_disclaimer: 'The final determination belongs to the reviewing teacher.',
        provider:        'demo',
        is_fallback:     false,
        latency_ms:      0,
        success:         true,
        degraded:        false,
        has_evidence_label:  true,
        has_policy_label:    true,
        has_inference_label: true,
        has_disclaimer:      true,
        mcp_summary_available: false,
        rag_policy_available:  false,
      });
    } finally {
      setExplainLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0f1e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#6b7280', fontSize: 14 }}>Loading session...</span>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0f1e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#ef4444', fontSize: 14 }}>Session not found.</span>
      </div>
    );
  }

  const AI_DETECTION_CONFIG: Record<string, { label: string; color: string }> = {
    DETECTED:     { label: 'AI Signal: DETECTED',     color: '#ef4444' },
    SUSPECTED:    { label: 'AI Signal: SUSPECTED',    color: '#f97316' },
    NOT_DETECTED: { label: 'AI Signal: Not Detected', color: '#10b981' },
    UNOBSERVABLE: { label: 'AI Signal: Unobservable', color: '#6b7280' },
  };
  const aiCfg = AI_DETECTION_CONFIG[session.aiDetectionState] ?? AI_DETECTION_CONFIG.UNOBSERVABLE;

  return (
    <div style={{ minHeight: '100vh', background: '#0a0f1e', color: '#f9fafb', fontFamily: 'inherit' }}>
      {/* Top bar */}
      <div
        style={{
          borderBottom: '1px solid #1f2937',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          height: 56,
          gap: 16,
        }}
      >
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            background: 'transparent', border: 'none', color: '#6b7280',
            fontSize: 14, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          ← Dashboard
        </button>
        <span style={{ color: '#374151' }}>|</span>
        <span style={{ color: '#9ca3af', fontSize: 13 }}>Session Review</span>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px' }}>
        {/* Session header */}
        <div
          ref={headerRef}
          style={{
            background: '#111827',
            border: '1px solid #1f2937',
            borderRadius: 8,
            padding: '20px 24px',
            marginBottom: 20,
            display: 'grid',
            gridTemplateColumns: '1fr auto',
            gap: 24,
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <RiskBadge level={session.riskLevel} score={session.riskScore} size="lg" />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: aiCfg.color,
                  background: `${aiCfg.color}18`,
                  border: `1px solid ${aiCfg.color}40`,
                  borderRadius: 4,
                  padding: '2px 10px',
                }}
              >
                {aiCfg.label}
              </span>
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#f9fafb', marginBottom: 4 }}>
              {session.studentName}
            </h2>
            <div style={{ fontSize: 13, color: '#6b7280' }}>
              {session.examTitle} &nbsp;·&nbsp; {session.eventCount} events &nbsp;·&nbsp;{' '}
              {new Date(session.startedAt).toLocaleString()}
            </div>
          </div>
          <div style={{ minWidth: 200 }}>
            <RiskScoreBar score={session.riskScore} level={session.riskLevel} />
          </div>
        </div>

        {/* Two-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
          {/* Left: timeline + explanation */}
          <div>
            <Section title={`Evidence Timeline — ${events.length} events`}>
              <EventTimeline events={events} />
            </Section>

            <ExplanationPanel
              explanation={explanation}
              loading={explainLoading}
              onRequest={handleRequestExplanation}
            />
          </div>

          {/* Right: sidebar */}
          <div>
            {/* Session metadata */}
            <Section title="Session Info">
              <div style={{ padding: '12px 16px' }}>
                {[
                  ['Session ID',  session.id],
                  ['Student ID',  session.studentId],
                  ['Exam ID',     session.examId],
                  ['Status',      session.status],
                  ['Started',     new Date(session.startedAt).toLocaleString()],
                  ['Events',      String(session.eventCount)],
                ].map(([k, v]) => (
                  <div
                    key={k}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '5px 0',
                      borderBottom: '1px solid #1a2234',
                      fontSize: 12,
                    }}
                  >
                    <span style={{ color: '#6b7280' }}>{k}</span>
                    <span style={{ color: '#d1d5db', fontFamily: k === 'Session ID' ? 'monospace' : 'inherit', fontSize: 11 }}>
                      {v}
                    </span>
                  </div>
                ))}
              </div>
            </Section>

            {/* Provider health */}
            <ProviderHealthPanel health={health} />

            {/* Important note */}
            <div
              style={{
                marginTop: 16,
                background: 'rgba(99,102,241,0.06)',
                border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 8,
                padding: '12px 14px',
                fontSize: 11,
                color: '#818cf8',
                lineHeight: 1.7,
              }}
            >
              This review is based on observable behavioral signals only. No automated verdict is issued.
              The final determination of academic integrity always belongs to the teacher or institution.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionDetailPage;
