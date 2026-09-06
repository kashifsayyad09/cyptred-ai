import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { gsap } from 'gsap';
import './ExamPage.css';

// Extension bridge — communicates with the Manifest V3 extension
import { startExamSession, endExamSession, isExtensionPresent } from '../../extension/src/extensionBridge';

type MonitoringStatus = 'checking' | 'active' | 'inactive';
type ConnectionStatus = 'connecting' | 'connected' | 'error';

const DEMO_EXAM = {
  title: 'Sample Examination',
  durationMinutes: 60,
  questions: [
    { id: 1, text: 'Explain the concept of algorithmic complexity using an example.' },
    { id: 2, text: 'Describe the difference between a stack and a queue data structure.' },
    { id: 3, text: 'What is the purpose of database indexing? Give two advantages.' },
  ],
};

const ExamPage: React.FC = () => {
  const { examId } = useParams<{ examId: string }>();
  const [monitorStatus, setMonitorStatus] = useState<MonitoringStatus>('checking');
  const [connStatus, setConnStatus] = useState<ConnectionStatus>('connecting');
  const [timeLeft, setTimeLeft] = useState(DEMO_EXAM.durationMinutes * 60);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [consentGiven, setConsentGiven] = useState(false);
  const [examStarted, setExamStarted] = useState(false);

  const headerRef = useRef<HTMLElement>(null);
  const timerRef = useRef<HTMLDivElement>(null);

  // ── GSAP entrance ─────────────────────────────────────────────────────────
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.exam-header', { opacity: 0, y: -20, duration: 0.5, ease: 'power2.out' });
      gsap.from('.exam-question', { opacity: 0, y: 20, stagger: 0.1, duration: 0.4, delay: 0.3 });
    }, headerRef);
    return () => ctx.revert();
  }, [examStarted]);

  // ── Check extension ────────────────────────────────────────────────────────
  useEffect(() => {
    isExtensionPresent().then((present) => {
      setMonitorStatus(present ? 'active' : 'inactive');
      setConnStatus(present ? 'connected' : 'connecting');
    });
  }, []);

  // ── Countdown timer ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!examStarted) return;
    const id = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { clearInterval(id); return 0; }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [examStarted]);

  // ── Start exam + extension session ────────────────────────────────────────
  function handleStartExam() {
    const sessionId = `demo-${Date.now()}`;
    const token = localStorage.getItem('access_token') || 'demo-token';
    startExamSession({ sessionId, token, examId: examId || 'demo', apiBase: '/api/v1' });
    setExamStarted(true);
  }

  // ── Submit / end ──────────────────────────────────────────────────────────
  function handleSubmit() {
    endExamSession();
    setExamStarted(false);
    alert('Exam submitted. Thank you!');
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function formatTime(secs: number) {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  // ── Consent screen ────────────────────────────────────────────────────────
  if (!consentGiven) {
    return (
      <div className="exam-consent">
        <div className="exam-consent__box">
          <h1>🛡 AI Exam Guardian</h1>
          <h2>Before you begin</h2>
          <p>
            This exam uses the <strong>AI Exam Guardian</strong> extension to
            monitor exam integrity. The following signals are collected during
            your session:
          </p>
          <ul>
            <li>Window focus and blur events</li>
            <li>Tab switch signals</li>
            <li>Copy and paste events (paste length only — not content)</li>
            <li>Fullscreen exit events</li>
            <li>Common DevTools keyboard shortcuts</li>
          </ul>
          <p className="consent-warning">
            <strong>Not collected:</strong> passwords, clipboard text,
            browsing history, or any data outside this exam session.
          </p>
          <p>
            The collected signals are reviewed by your teacher if anomalies
            are detected. No automated verdict is ever issued — your teacher
            makes the final determination.
          </p>
          <button className="btn btn--primary" onClick={() => setConsentGiven(true)}>
            I understand and consent — Begin Exam
          </button>
        </div>
      </div>
    );
  }

  // ── Pre-start screen ──────────────────────────────────────────────────────
  if (!examStarted) {
    return (
      <div className="exam-prestart">
        <div className="exam-prestart__box">
          <h1>{DEMO_EXAM.title}</h1>
          <p>Duration: <strong>{DEMO_EXAM.durationMinutes} minutes</strong></p>
          <p>Questions: <strong>{DEMO_EXAM.questions.length}</strong></p>
          <div className={`monitor-badge monitor-badge--${monitorStatus}`}>
            Extension: {monitorStatus === 'active' ? '✓ Monitoring active' : '⚠ Extension not detected'}
          </div>
          <button className="btn btn--primary" onClick={handleStartExam}>
            Start Exam
          </button>
        </div>
      </div>
    );
  }

  // ── Active exam ───────────────────────────────────────────────────────────
  return (
    <div className="exam-page" ref={headerRef}>
      <header className="exam-header">
        <div className="exam-header__left">
          <span className="exam-title">{DEMO_EXAM.title}</span>
        </div>
        <div className="exam-header__center">
          <div ref={timerRef} className={`exam-timer ${timeLeft < 300 ? 'exam-timer--warning' : ''}`}>
            ⏱ {formatTime(timeLeft)}
          </div>
        </div>
        <div className="exam-header__right">
          <span className={`conn-status conn-status--${connStatus}`}>
            {connStatus === 'connected' ? '● Connected' : '○ Connecting'}
          </span>
          <span className={`monitor-dot monitor-dot--${monitorStatus}`} title={`Monitoring: ${monitorStatus}`} />
        </div>
      </header>

      <main className="exam-main">
        {DEMO_EXAM.questions.map((q) => (
          <div key={q.id} className="exam-question">
            <label className="question-label">
              <span className="question-number">Q{q.id}</span>
              {q.text}
            </label>
            <textarea
              className="question-answer"
              rows={6}
              placeholder="Type your answer here…"
              value={answers[q.id] ?? ''}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
            />
          </div>
        ))}

        <div className="exam-submit">
          <button className="btn btn--primary btn--large" onClick={handleSubmit}>
            Submit Exam
          </button>
        </div>
      </main>
    </div>
  );
};

export default ExamPage;
