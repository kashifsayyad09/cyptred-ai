/**
 * DashboardPage — Teacher dashboard root.
 *
 * Shows:
 *  - Summary stats bar (total sessions, flagged, high priority, active)
 *  - Session list with risk badges, event counts, AI detection state
 *  - Clicking a session opens SessionDetailPage
 *
 * Uses mock data when the backend is unavailable (dev mode).
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import RiskBadge from '../components/RiskBadge';
import { fetchSessions } from '../api/dashboard';
import type { ExamSession } from '../types';

// ── Mock data (used when backend unavailable) ─────────────────────────────────

const MOCK_SESSIONS: ExamSession[] = [
  {
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
  },
  {
    id: 'sess-002',
    examId: 'exam-001',
    examTitle: 'Advanced Algorithms Midterm',
    studentId: 'stu-102',
    studentName: 'Student B',
    startedAt: '2025-01-15T10:31:12Z',
    riskScore: 65,
    riskLevel: 'REVIEW_REQUIRED',
    aiDetectionState: 'SUSPECTED',
    eventCount: 8,
    status: 'flagged',
  },
  {
    id: 'sess-003',
    examId: 'exam-001',
    examTitle: 'Advanced Algorithms Midterm',
    studentId: 'stu-103',
    studentName: 'Student C',
    startedAt: '2025-01-15T10:30:58Z',
    riskScore: 35,
    riskLevel: 'ATTENTION',
    aiDetectionState: 'NOT_DETECTED',
    eventCount: 4,
    status: 'active',
  },
  {
    id: 'sess-004',
    examId: 'exam-002',
    examTitle: 'Data Structures Final',
    studentId: 'stu-201',
    studentName: 'Student D',
    startedAt: '2025-01-15T14:00:01Z',
    riskScore: 10,
    riskLevel: 'NORMAL',
    aiDetectionState: 'NOT_DETECTED',
    eventCount: 1,
    status: 'active',
  },
  {
    id: 'sess-005',
    examId: 'exam-002',
    examTitle: 'Data Structures Final',
    studentId: 'stu-202',
    studentName: 'Student E',
    startedAt: '2025-01-15T14:00:09Z',
    riskScore: 20,
    riskLevel: 'MONITORING',
    aiDetectionState: 'NOT_DETECTED',
    eventCount: 3,
    status: 'active',
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const AI_DETECTION_CONFIG: Record<string, { label: string; color: string }> = {
  DETECTED:     { label: 'Detected',     color: '#ef4444' },
  SUSPECTED:    { label: 'Suspected',    color: '#f97316' },
  NOT_DETECTED: { label: 'Not detected', color: '#10b981' },
  UNOBSERVABLE: { label: 'Unobservable', color: '#6b7280' },
};

const STATUS_LABEL: Record<string, string> = {
  active:    'Active',
  completed: 'Completed',
  flagged:   'Flagged',
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

// ── Summary stat card ─────────────────────────────────────────────────────────

const StatCard: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => (
  <div
    style={{
      flex: 1,
      background: '#111827',
      border: '1px solid #1f2937',
      borderRadius: '8px',
      padding: '16px 20px',
      minWidth: 120,
    }}
  >
    <div style={{ fontSize: '28px', fontWeight: 700, color }}>{value}</div>
    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: 4 }}>{label}</div>
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

const DashboardPage: React.FC = () => {
  const [sessions, setSessions] = useState<ExamSession[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [filter, setFilter]     = useState<string>('all');
  const listRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSessions()
      .then((data) => {
        if (!cancelled) setSessions(data.length > 0 ? data : MOCK_SESSIONS);
      })
      .catch(() => {
        if (!cancelled) {
          setSessions(MOCK_SESSIONS);
          setError('Using demo data — backend unavailable');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  // Animate rows in on load
  useEffect(() => {
    if (!listRef.current || loading) return;
    const rows = listRef.current.querySelectorAll('[data-row]');
    gsap.fromTo(
      rows,
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.3, stagger: 0.04, ease: 'power2.out' },
    );
  }, [loading, sessions]);

  const filtered = sessions.filter((s) => {
    if (filter === 'all')      return true;
    if (filter === 'flagged')  return s.status === 'flagged';
    if (filter === 'active')   return s.status === 'active';
    if (filter === 'review')   return ['REVIEW_REQUIRED', 'HIGH_PRIORITY_REVIEW'].includes(s.riskLevel);
    return true;
  });

  const stats = {
    total:       sessions.length,
    flagged:     sessions.filter(s => s.status === 'flagged').length,
    high:        sessions.filter(s => s.riskLevel === 'HIGH_PRIORITY_REVIEW').length,
    active:      sessions.filter(s => s.status === 'active').length,
  };

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
          gap: 24,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 16, color: '#f9fafb', letterSpacing: '0.01em' }}>
          AI Exam Guardian
        </span>
        <span style={{ color: '#374151', fontSize: 18 }}>|</span>
        <span style={{ color: '#6b7280', fontSize: 14 }}>Teacher Dashboard</span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
        </span>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 24px' }}>
        {/* Error banner */}
        {error && (
          <div
            style={{
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.3)',
              borderRadius: 6,
              padding: '8px 14px',
              fontSize: 12,
              color: '#f59e0b',
              marginBottom: 20,
            }}
          >
            {error}
          </div>
        )}

        {/* Stats row */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <StatCard label="Total Sessions"   value={stats.total}   color="#f9fafb" />
          <StatCard label="Flagged"          value={stats.flagged} color="#f97316" />
          <StatCard label="High Priority"    value={stats.high}    color="#ef4444" />
          <StatCard label="Active Now"       value={stats.active}  color="#3b82f6" />
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
          {[
            { key: 'all',     label: 'All Sessions' },
            { key: 'review',  label: 'Review Required' },
            { key: 'flagged', label: 'Flagged' },
            { key: 'active',  label: 'Active' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              style={{
                background: filter === tab.key ? '#3b82f6' : 'transparent',
                color:      filter === tab.key ? '#fff'    : '#6b7280',
                border:     filter === tab.key ? 'none'    : '1px solid #1f2937',
                borderRadius: 6,
                padding: '6px 14px',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Session table */}
        <div
          style={{
            background: '#111827',
            border: '1px solid #1f2937',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 140px 110px 90px 80px',
              gap: '0.5rem',
              padding: '10px 16px',
              background: '#0d1322',
              borderBottom: '1px solid #1f2937',
              fontSize: 11,
              fontWeight: 700,
              color: '#6b7280',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}
          >
            <span>Student / Exam</span>
            <span>Risk</span>
            <span>AI Detection</span>
            <span>Events</span>
            <span>Status</span>
            <span>Started</span>
          </div>

          {/* Rows */}
          <div ref={listRef}>
            {loading && (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                Loading sessions...
              </div>
            )}
            {!loading && filtered.length === 0 && (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                No sessions match the current filter.
              </div>
            )}
            {!loading && filtered.map((session) => {
              const aiCfg = AI_DETECTION_CONFIG[session.aiDetectionState] ?? AI_DETECTION_CONFIG.UNOBSERVABLE;
              return (
                <div
                  key={session.id}
                  data-row
                  onClick={() => navigate(`/dashboard/session/${session.id}`)}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 140px 110px 90px 80px',
                    gap: '0.5rem',
                    padding: '12px 16px',
                    borderBottom: '1px solid #1a2234',
                    cursor: 'pointer',
                    transition: 'background 0.12s',
                    alignItems: 'center',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#0f172a')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Student / Exam */}
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#f3f4f6' }}>
                      {session.studentName}
                    </div>
                    <div style={{ fontSize: 11, color: '#4b5563', marginTop: 2 }}>
                      {session.examTitle}
                    </div>
                  </div>

                  {/* Risk */}
                  <RiskBadge level={session.riskLevel} score={session.riskScore} size="sm" />

                  {/* AI Detection */}
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: aiCfg.color,
                    }}
                  >
                    {aiCfg.label}
                  </span>

                  {/* Event count */}
                  <span style={{ fontSize: 13, color: '#9ca3af' }}>
                    {session.eventCount} events
                  </span>

                  {/* Status */}
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color:
                        session.status === 'flagged'   ? '#f97316' :
                        session.status === 'active'    ? '#3b82f6' :
                                                         '#6b7280',
                    }}
                  >
                    {STATUS_LABEL[session.status] ?? session.status}
                  </span>

                  {/* Time */}
                  <span style={{ fontSize: 11, color: '#4b5563', fontFamily: 'monospace' }}>
                    {formatTime(session.startedAt)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Disclaimer */}
        <p
          style={{
            marginTop: 20,
            fontSize: 11,
            color: '#374151',
            lineHeight: 1.6,
          }}
        >
          AI Exam Guardian provides evidence for teacher review — not automated verdicts.
          The final determination of academic integrity always belongs to the teacher or institution.
        </p>
      </div>
    </div>
  );
};

export default DashboardPage;
