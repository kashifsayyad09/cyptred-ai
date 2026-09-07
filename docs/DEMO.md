# AI Exam Guardian — Demo Walkthrough

> **Version:** 1.0  
> **Phase:** 12 — Final QA + Demo  
> **For:** Hackathon judges, evaluators, and new developers

---

## ⚠️ Important Notice

AI Exam Guardian is a **privacy-first evidence collection system**. It does not make automated determinations about academic integrity. Every risk flag is a signal for **human review**. The final judgment always belongs to the teacher or institution.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Development Setup](#2-local-development-setup)
3. [Demo Scenario — Step by Step](#3-demo-scenario--step-by-step)
4. [Simulated Incident Timeline](#4-simulated-incident-timeline)
5. [Teacher Dashboard Walkthrough](#5-teacher-dashboard-walkthrough)
6. [Provider Failover Demo](#6-provider-failover-demo)
7. [False Positive Verification](#7-false-positive-verification)
8. [Running the Tests](#8-running-the-tests)
9. [Known Limitations](#9-known-limitations)

---

## 1. Prerequisites

| Tool | Version | Required for |
|------|---------|-------------|
| Python | 3.11+ | Backend, MCP, RAG |
| Node.js | 20+ | Frontend, extension tests |
| Docker | 24+ | Full stack |
| Docker Compose | v2 | Orchestration |
| Chrome/Edge | Latest | Extension |

> For local development without Docker, Python 3.14 works for pure-logic tests.
> The full stack (FastAPI, Starlette, prometheus_client) requires Python 3.11 (use Docker).

---

## 2. Local Development Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-org/ai-exam-guardian.git
cd ai-exam-guardian

# 2. Copy environment template
cp .env.example .env
# Edit .env — add your Groq and NVIDIA API keys

# 3. Start full stack
cd infra
docker compose up -d --build

# 4. Verify all services are healthy
docker compose ps
curl http://localhost/health        # → {"status":"ok"}
curl http://localhost/ready         # → {"status":"ready","checks":{...}}

# 5. Access services
# Frontend:   http://localhost
# Grafana:    http://localhost:3001  (admin / from .env)
# Prometheus: http://localhost:9090
```

---

## 3. Demo Scenario — Step by Step

This scenario demonstrates the full detection pipeline.

### Step 1 — Student starts exam

1. Open `http://localhost` in Chrome/Edge
2. Install the browser extension from `extension/` (Developer mode → Load unpacked)
3. Log in as a student (create via API or seed script)
4. Start an exam session

**Expected state:** Risk score = 0, Status = NORMAL

---

### Step 2 — Normal behaviour (no flags)

The student reads questions and types normally.

**Expected state:** Risk score stays at 0–15, Status = NORMAL

---

### Step 3 — Focus loss event

Switch to another window briefly (or trigger the event via the extension popup).

**Expected:** Risk score += 5 (FOCUS_LOSS weight)

**Teacher dashboard:** Still NORMAL (score 5)

---

### Step 4 — External navigation signal

Navigate to an external site from a different tab.

**Expected:** Risk score += 20 (SUSPICIOUS_NAVIGATION weight)

**Teacher dashboard:** Score = 25 → Status: MONITORING

---

### Step 5 — ParakeetAI signal (primary demo moment)

Navigate to `https://www.parakeet-ai.com/` in the same browser session.

**Expected from MCP:**
- AI Assistant Detector fires
- `parakeet-ai.com` matched in registry
- Detection state: DETECTED or SUSPECTED
- Risk score += 25 (AI_ASSISTANT_SIGNAL weight)

**Teacher dashboard:** Score = 50 → Status: ATTENTION

---

### Step 6 — Return to exam + Copy/Paste sequence

Return to the exam tab. Copy text from an answer. Paste it into the exam.

**Expected:**
- COPY event: +15
- PASTE event: +15
- Correlation engine detects `focus_loss_navigation_paste` sequence

**Teacher dashboard:** Score = 80 → Status: **HIGH_PRIORITY_REVIEW** 🔴

---

### Step 7 — MCP correlation fires

The MCP Correlation Engine detects the full sequence:

```
FOCUS_LOSS
→ SUSPICIOUS_NAVIGATION
→ AI_ASSISTANT_SIGNAL (parakeet-ai.com)
→ COPY
→ PASTE
```

This matches the `focus_loss_navigation_paste` and potentially `ai_navigation_paste` sequences.

**Sequence bonus:** +20 additional score (capped at 100).

---

### Step 8 — RAG retrieves exam policy

The system retrieves the AI assistance policy from the RAG store:

```
"AI assistants, including but not limited to ChatGPT, Claude, Gemini,
Microsoft Copilot, Perplexity, and ParakeetAI, are prohibited during
this examination."
```

---

### Step 9 — Groq generates explanation

The AI Gateway calls Groq (PRIMARY) with:
- The evidence timeline
- The RAG-retrieved policy
- The risk score and level

**Example AI explanation output:**

```
Review recommended. The session contains the following observable signals:
• Focus loss event at 10:42:11
• External navigation signal at 10:42:18
• Navigation to parakeet-ai.com at 10:43:02 (AI assistant signal: SUSPECTED)
• Copy event at 10:42:45
• Paste event at 10:42:49

Under the configured exam policy, AI assistants including ParakeetAI are
prohibited. The combination of AI-domain navigation, copy, and paste events
is consistent with AI-assisted answer insertion. This evidence does not by
itself establish intentional cheating and requires teacher review.
```

**Note:** The AI explanation clearly labels:
- `OBSERVED EVIDENCE` — what the system recorded
- `POLICY INTERPRETATION` — what the retrieved policy says
- `AI INFERENCE` — what the model is concluding

---

### Step 10 — Teacher sees REVIEW REQUIRED

Open `http://localhost/dashboard` as a teacher.

The session appears in the **Review Required** tab with:
- Risk score: 80–100
- Status badge: HIGH PRIORITY REVIEW (red)
- Event timeline with all 5+ events
- AI explanation panel
- Policy references from RAG

---

## 4. Simulated Incident Timeline

```
10:31:04  Exam started                        Score:  0   NORMAL
10:42:11  Focus lost                           Score:  5   NORMAL
10:42:18  External navigation signal           Score: 25   MONITORING
10:42:41  Returned to exam tab                 Score: 25   MONITORING
10:42:45  Copy event                           Score: 40   ATTENTION
10:42:49  Paste event                          Score: 55   ATTENTION
10:43:02  AI assistant signal (parakeet-ai)    Score: 80   HIGH_PRIORITY_REVIEW
10:43:02  Sequence bonus applied               Score: 80   HIGH_PRIORITY_REVIEW (capped)
10:43:05  RAG policy retrieved                 —
10:43:06  Groq explanation generated           —
10:43:07  Incident stored in DB                —
```

---

## 5. Teacher Dashboard Walkthrough

### Dashboard page (`/dashboard`)

Shows all active exam sessions with:
- **NORMAL** (green) — no signals
- **MONITORING** (yellow) — early signals
- **ATTENTION** (orange) — multiple signals
- **REVIEW REQUIRED** (red) — requires human review
- **HIGH PRIORITY REVIEW** (dark red) — urgent

Filter tabs: All Sessions | Needs Review | AI Signals | Active

### Session Detail page (`/dashboard/session/:id`)

Shows:
- Animated risk score bar (GSAP)
- Evidence timeline (chronological, colour-coded by severity)
- AI explanation panel with labelled sections
- Provider health status (Groq / NVIDIA)
- Session metadata (duration, event count, exam name)

### Regenerate explanation

Click "Regenerate" in the Explanation Panel to call the AI Gateway again with updated evidence.

---

## 6. Provider Failover Demo

### Groq → NVIDIA automatic failover

To simulate Groq failure, set an invalid Groq API key:

```bash
# In .env
GROQ_API_KEY=invalid_key_for_demo

# Restart backend
docker compose restart backend

# Make an explanation request
curl -X POST http://localhost/api/v1/explain \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session-001"}'
```

**Expected:** NVIDIA NIM is used as fallback. Check logs:

```bash
docker compose logs backend | grep "fallback"
# → "fallback_activated": true, "provider": "nvidia"
```

### Both providers unavailable — degraded response

```bash
# Set both keys to invalid
GROQ_API_KEY=invalid
NVIDIA_API_KEY=invalid

# Explanation request still returns HTTP 200 with degraded response
# Risk score from Rules Engine is still accurate
# AI explanation is replaced with deterministic fallback text
```

**Expected:** Rules Engine continues to score correctly. No crashes. Teacher sees deterministic summary.

---

## 7. False Positive Verification

### Normal exam session stays NORMAL

```python
from mcp.rules.rules_engine import RulesEngine, EventType

engine = RulesEngine()

# Normal events: one focus loss + one tab switch
events = [
    {"event_type": "FOCUS_LOSS", "occurred_at": "2024-01-15T10:31:00Z", "metadata": {}},
    {"event_type": "TAB_SWITCH", "occurred_at": "2024-01-15T10:32:00Z", "metadata": {}},
]

result = engine.evaluate(events)
print(f"Score: {result.total_score}")  # → 15
print(f"Level: {result.risk_level}")   # → NORMAL
```

### Unrelated domain navigation is not flagged

```python
from mcp.detectors.ai_assistant_detector import AIAssistantDetector

detector = AIAssistantDetector()
events = [{
    "event_type": "SUSPICIOUS_NAVIGATION",
    "occurred_at": "2024-01-15T10:31:00Z",
    "metadata": {"toUrl": "https://www.google.com/"},
}]

report = detector.detect(events, session_id="test")
print(report.overall_state)  # → NOT_DETECTED or UNOBSERVABLE
```

---

## 8. Running the Tests

### All tests (native Python 3.14)

```bash
# Root-level integration tests (Phase 12)
python -m pytest tests/test_phase12.py -v

# MCP unit tests (Phase 4 + 5)
python -m pytest mcp/tests/ -v

# RAG tests (Phase 6)
python -m pytest rag/tests/ -v

# AI Gateway tests (Phase 7 + 8)
python -m pytest tests/test_ai_gateway.py -v

# Backend tests (Phase 2 + 7 + 8 + 10 + 11)
python -m pytest backend/tests/ -v --rootdir=backend

# Extension tests (Node.js)
node extension/tests/test_extension.mjs
```

### Full test suite

```bash
python -m pytest tests/ mcp/tests/ rag/tests/ -v
python -m pytest backend/tests/ --rootdir=backend -v
node extension/tests/test_extension.mjs
```

### Expected results (as of Phase 12)

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 12 integration | 88 pass + 4 skip | ✅ |
| Backend (all phases) | 263 pass + 48 skip | ✅ |
| MCP + RAG + Root | 147 pass | ✅ |
| Extension JS | 37 pass | ✅ |
| **TOTAL** | **535 pass / 0 fail** | ✅ |

---

## 9. Known Limitations

| Limitation | Explanation |
|-----------|-------------|
| Cannot detect all ParakeetAI usage | ParakeetAI is specifically designed to evade detection. Absence of a signal does not prove it was not used. |
| Browser API restrictions | Manifest V3 limits available APIs. Navigation signals are observable; desktop activity is not. |
| Single session correlation only | Cross-session pattern analysis is a future enhancement. |
| AI explanations are probabilistic | LLM output varies. The deterministic risk score is the authoritative signal, not the explanation. |
| Local setup needs real API keys | Groq and NVIDIA keys are required for AI explanations. Rules Engine works without them. |
| Unsigned Electron build | Desktop app is not production-ready without platform signing (see `desktop/` notes). |

---

## Quick Reference

### Risk Level Thresholds

| Score | Level | Badge |
|-------|-------|-------|
| 0–19 | NORMAL | 🟢 |
| 20–39 | MONITORING | 🟡 |
| 40–59 | ATTENTION | 🟠 |
| 60–79 | REVIEW REQUIRED | 🔴 |
| 80–100 | HIGH PRIORITY REVIEW | 🔴🔴 |

### Detection States

| State | Meaning |
|-------|---------|
| DETECTED | Observable signals strongly associated with AI assistant use |
| SUSPECTED | Behavioral patterns consistent with AI assistant use |
| NOT_DETECTED | No observable signals found |
| UNOBSERVABLE | Activity cannot be observed by available browser APIs |

---

*This document is part of the AI Exam Guardian project. For full technical documentation, see [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/SECURITY.md`](SECURITY.md), and the [`README.md`](../README.md).*
