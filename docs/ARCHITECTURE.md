# AI Exam Guardian — Architecture Documentation

## Overview

AI Exam Guardian is a privacy-first online exam integrity platform. It detects and correlates suspicious exam-session behavior and potential unauthorized AI-assistant usage using a layered, evidence-based approach.

**Important:** No browser-based system can detect cheating or external software with 100% certainty. This system provides layered evidence for teacher review. The final decision always belongs to the teacher or institution.

---

## System Architecture

```
Student Browser
    │
    ├── React Exam Website (frontend/)
    │       └── Exam UI, timer, questions, status indicators
    │
    └── Chrome/Edge Extension (extension/)
            └── Manifest V3 — event capture, telemetry
                    │
                    ▼
            FastAPI Backend (backend/)
            ├── Authentication (JWT)
            ├── Exam/Session APIs
            ├── Event Ingestion API
            ├── Risk API
            └── Health API
                    │
                    ▼
            MCP Server (mcp/)
            ├── Event Validation
            ├── AI Assistant Detection
            │       └── detectors/ai_assistant_detector/
            ├── Behavioral Rules Engine
            ├── Evidence Correlation
            └── Deterministic Risk Engine
                    │
                    ▼
            RAG Engine (rag/)
            ├── Exam Policies
            ├── Institution Policies
            ├── Allowed/Prohibited Resources
            ├── AI Usage Policy
            └── Review Guidelines
                    │
                    ▼
            AI Gateway
            ├── Groq (PRIMARY)
            └── NVIDIA NIM (AUTOMATIC FALLBACK)
                    │
                    ▼
            AWS RDS MySQL
                    │
                    ▼
            Teacher Dashboard (frontend/)
            └── Sessions, Risk Scores, Evidence, Timeline, Incidents
```

---

## Component Descriptions

### React Exam Website
- Student-facing exam interface
- Displays exam title, timer, questions, connection status, monitoring status
- GSAP micro-interactions
- Communicates with FastAPI backend

### Chrome/Edge Extension (Manifest V3)
- Captures permitted exam telemetry only
- Events: focus, blur, tab changes, navigation signals, copy, paste, fullscreen, keyboard shortcuts, exam lifecycle
- Sends events securely to FastAPI
- Minimal permissions — only what exam integrity requires
- Clear consent and exam-policy disclosure shown to student

### FastAPI Backend
- Handles authentication (JWT)
- Exam and session management
- Event ingestion from extension
- Risk score retrieval
- Passes events to MCP Server
- Health endpoints for all services

### MCP Server
- Dedicated Docker container
- Exposes structured MCP tools:
  - check_focus_loss, check_tab_switch, check_copy, check_paste
  - check_navigation, check_fullscreen, check_keyboard_shortcuts
  - check_devtools_signal, check_ai_assistant_signal
  - correlate_behavior, calculate_risk
  - get_exam_rules, get_policy, get_student_timeline
  - create_incident_summary

### Behavioral Rules Engine
- Fully deterministic — no LLM involvement in scoring
- Configurable scoring weights (not hardcoded)
- Default scores:
  - TAB_SWITCH: +10
  - FOCUS_LOSS: +5
  - COPY: +15
  - PASTE: +15
  - FULLSCREEN_EXIT: +10
  - SUSPICIOUS_NAVIGATION: +20
  - AI_ASSISTANT_SIGNAL: +25
  - REPEATED_VIOLATIONS: +20
  - SUSPICIOUS_SEQUENCE: +20
- Risk states: NORMAL (0–19), MONITORING (20–39), ATTENTION (40–59), REVIEW_REQUIRED (60–79), HIGH_PRIORITY_REVIEW (80–100)

### AI Assistant Detection
- Location: mcp/detectors/ai_assistant_detector/
- Targets: ParakeetAI, ChatGPT, Claude, Gemini, Microsoft Copilot, Perplexity, configurable others
- Detection outputs: DETECTED | SUSPECTED | NOT_DETECTED | UNOBSERVABLE
- Defense in depth — domain signals, behavioral patterns, sequence correlation
- Does NOT claim 100% detection
- ParakeetAI primary target: parakeet-ai.com (+ www., app., subdomains)

### Correlation Engine
- Sequences produce stronger signals than individual events
- Creates evidence timeline: timestamp, event, source, rule, severity, score contribution, confidence, metadata
- Example high-signal sequence: AI domain navigation → return to exam → copy → paste → rapid answer modification

### RAG System
- Retrieves: exam rules, institution policies, AI-assistance policy, allowed/prohibited resources, review procedures, incident guidance
- Does NOT invent policies
- Every AI explanation distinguishes: OBSERVED EVIDENCE vs POLICY INTERPRETATION vs AI INFERENCE
- Metadata filtering by: exam, institution, policy, document type

### AI Gateway
- Groq: PRIMARY provider
- NVIDIA NIM: AUTOMATIC FALLBACK
- Failover triggers: timeout, 429, 5xx, quota exhaustion, token/context limit, connection error, empty response, invalid response
- Automatic Groq restoration when healthy
- Full logging: provider, request ID, failure reason, HTTP status, latency, fallback activation, timestamp
- API keys NEVER exposed to client-side code

### AWS RDS MySQL
- Tables: users, students, teachers, exams, exam_rules, exam_sessions, events, risk_scores, incidents, evidence, ai_provider_logs, rag_documents, rag_chunks, audit_logs
- Proper indexes
- Migration-based schema management

### Teacher Dashboard
- Pages: Dashboard, Exams, Active Sessions, Incident Review, Student Detail, Evidence Timeline, Policies, AI Provider Health
- Risk status display: NORMAL, MONITORING, ATTENTION, REVIEW REQUIRED, HIGH PRIORITY REVIEW
- Full evidence timeline with timestamps and event details
- AI-generated explanations of correlated evidence
- Policy references from RAG

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Student Frontend | React, GSAP |
| Teacher Dashboard | React, GSAP |
| Browser Extension | Manifest V3 (Chrome/Edge) |
| Backend API | Python FastAPI |
| MCP Server | Python, MCP SDK |
| RAG System | Python, vector retrieval |
| AI Gateway | Python (Groq + NVIDIA NIM) |
| Database | AWS RDS MySQL |
| Containerization | Docker, Docker Compose |
| Reverse Proxy | Nginx |
| Observability | Prometheus, Grafana |
| CI/CD | GitHub Actions |
| Container Registry | AWS ECR |
| Security Scanning | Trivy |
| Infrastructure | Terraform |
| Desktop (future) | Electron |

---

## Security Model

- HTTPS-ready (Nginx TLS termination)
- JWT authentication
- RBAC (teacher vs student roles)
- CORS restrictions
- Rate limiting
- Input validation on all endpoints
- Secure headers (HSTS, CSP, X-Frame-Options, etc.)
- Audit logging
- Container security hardening
- Trivy CVE scanning in CI/CD
- Secrets via environment variables only — never committed

---

## Deployment Architecture (Initial)

```
Internet
    │
  Nginx (TLS termination, reverse proxy)
    │
  ┌─────────────────────────────────────┐
  │  Docker Compose (AWS EC2)           │
  │  ├── frontend   (React)             │
  │  ├── backend    (FastAPI)           │
  │  ├── mcp        (MCP Server)        │
  │  ├── rag        (RAG Engine)        │
  │  ├── prometheus                     │
  │  └── grafana                        │
  └─────────────────────────────────────┘
    │
  AWS RDS MySQL (managed, external)
```

Migration path to EKS documented but not deployed in Phase 11.

---

## Known Limitations

1. Browser-based telemetry is inherently limited — determined actors can circumvent it
2. ParakeetAI and similar tools are specifically designed to evade detection
3. Absence of detection signals does NOT prove innocence
4. The system provides evidence for human review, not automated verdicts
5. Extension permissions vary by browser version and enterprise policy
6. Desktop-based monitoring (Electron) provides stronger signals but requires installation consent
7. Network-level monitoring is not implemented in this MVP

---

## Future Enhancements

- EKS/Kubernetes deployment
- Desktop app with enhanced OS-level monitoring (with appropriate consent)
- Additional AI assistant detection targets
- Browser fingerprinting correlation
- Network traffic analysis integration
- LMS (Canvas, Moodle) integration
- Proctoring camera integration (optional, consent-based)
- Federated learning for behavioral models
