import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import './LandingPage.css';

const LandingPage: React.FC = () => {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.fromTo(headingRef.current, { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.9 })
      .fromTo(subtitleRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7 }, '-=0.4')
      .fromTo(ctaRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6 }, '-=0.3');
  }, []);

  return (
    <div className="landing">
      <nav className="landing__nav">
        <div className="landing__logo">
          <span className="landing__logo-icon">🛡</span>
          <span>AI Exam Guardian</span>
        </div>
      </nav>
      <main className="landing__hero">
        <h1 ref={headingRef} className="landing__heading">
          Exam Integrity,<br />Evidence-Based
        </h1>
        <p ref={subtitleRef} className="landing__subtitle">
          A privacy-first platform that detects and correlates suspicious exam-session
          behaviour. Layered signals. Human decisions. No false certainty.
        </p>
        <div ref={ctaRef} className="landing__cta">
          <a href="/dashboard" className="btn btn--primary">Teacher Dashboard</a>
          <a href="/exam/demo" className="btn btn--secondary">Student Demo</a>
        </div>
        <p className="landing__disclaimer">
          No browser-based system can detect cheating with 100% certainty.
          All final decisions belong to the teacher or institution.
        </p>
      </main>
    </div>
  );
};

export default LandingPage;
