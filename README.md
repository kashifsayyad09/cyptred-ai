# AI Exam Guardian

> **Privacy-first online exam integrity platform** — detects and correlates suspicious exam-session behavior and potential unauthorized AI-assistant usage using a layered, evidence-based approach.

---

## ⚠️ Important Disclaimer

No browser-based system can detect cheating or external software with 100% certainty. AI Exam Guardian provides **layered behavioral evidence** for teacher review. The system **never accuses a student based on a single signal**. The final integrity decision **always belongs to the teacher or institution**.

---

## Problem

Online exams face a growing challenge: AI assistants (ChatGPT, Claude, Gemini, Copilot, ParakeetAI, Perplexity, and others) can be used during exams in ways that are difficult to observe with traditional proctoring. Some tools — notably ParakeetAI (`parakeet-ai.com`) — are specifically designed to operate without triggering standard screen-share detection.

No single signal proves intent. But correlated behavioral patterns — combined with known AI-domain navigation, copy/paste sequences, and rapid answer modifications — provide meaningful evidence for human review.

---

## Solution

AI Exam Guardian implements **defense in depth**:

1. **Browser extension** captures permitted exam telemetry (focus, blur, navigation, copy, paste, fullscreen, keyboard shortcuts)
2. **MCP Server** validates events and applies deterministic behavioral rules
3. **AI Assistant Detection** module identifies signals from known AI assistant domains and behavioral patterns
4. **Correlation Engine** sequences events into evidence timelines
5. **RAG System** retrieves relevant exam and institution policies
6. **AI Gateway** (Groq PRIMARY / NVIDIA FALLBACK) generates explainable incident summaries
7. **Teacher Dashboard** presents evidence, risk scores, timelines, and policy context for human review

---

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full architecture documentation.

```
Student Browser
    ├── React Exam Website
    └── Chrome/Edge Extension (Manifest V3)
                │
                ▼
        FastAPI Backend
                │
                ▼
        MCP Server
        ├── Rules Engine
        ├── AI Assistant Detector
        └── Correlation Engine
                │
                ▼
        RAG Engine ──→ AI Gateway (Groq / NVIDIA)
                │
                ▼
        AWS RDS MySQL
                │
                ▼
        Teacher Dashboard
```

---

## Final Technology Stack

| Layer | Technology |
|-------|-----------|
| Student Frontend | React, GSAP |
| Teacher Dashboard | React, GSAP |
| Browser Extension | Manifest V3 (Chrome/Edge) |
| Backend API | Python FastAPI |
| MCP Server | Python, MCP SDK |
| RAG System | Python, vector retrieval |
| AI Gateway | Groq (primary) + NVIDIA NIM (fallback) |
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

## Repository Structure

```
ai-exam-guardian/
├── backend/          # FastAPI Python application
├── frontend/         # React exam website + teacher dashboard
├── extension/        # Manifest V3 Chrome/Edge extension
├── mcp/              # MCP server container
│   └── detectors/
│       └── ai_assistant_detector/
├── rag/              # RAG knowledge system
├── desktop/          # Electron wrapper (future)
├── infra/            # Terraform, Docker Compose, Nginx
├── tests/            # Automated test suites
├── docs/             # Architecture and API documentation
├── .bob/             # Bob AI rules
├── .env.example      # Environment variable template
├── docker-compose.yml
└── README.md
```

---

## Development Phases

| Phase | Name | Progress |
|-------|------|----------|
| 0 | Project Audit | ██████████ 100% |
| 1 | Foundation | ██████████ 100% |
| 2 | Database + FastAPI | ██████████ 100% |
| 3 | Browser Extension | ██████████ 100% |
| 4 | MCP Server + Rules Engine | ██████████ 100% |
| 5 | AI Assistant Detection | ██████████ 100% |
| 6 | RAG Knowledge System | ██████████ 100% |
| 7 | Groq + NVIDIA AI Gateway | ██████████ 100% |
| 8 | AI Explanation + RAG Integration | ██████████ 100% |
| 9 | Teacher Dashboard | ░░░░░░░░░░ 0% |
| 10 | Security + Observability | ░░░░░░░░░░ 0% |
| 11 | AWS Deployment | ░░░░░░░░░░ 0% |
| 12 | Final QA + Demo | ░░░░░░░░░░ 0% |

**Overall Progress: 78%**

---

## Current Phase

**Phase 8 — COMPLETE**

AI Explanation + RAG Integration fully implemented:
- `prompt_builder.py` — `IncidentPrompt` dataclass with structured `build()` / `validate()`. Enforces three mandatory sections: `[OBSERVED EVIDENCE]`, `[POLICY INTERPRETATION]`, `[AI INFERENCE]`. Policy is labelled as RETRIEVED — AI cannot extend it
- `FORBIDDEN_PHRASES` list — server-side detection of forbidden verdict language ("student cheated", "definitely cheated", etc.)
- `explanation_service.py` — `ExplanationOrchestrator` full pipeline: MCP summary → RAG policy → AI Gateway → output validation → forbidden phrase sanitisation
- `ExplanationResult.validate_output()` — post-generation check: labels present, disclaimer present, no forbidden phrases
- Graceful degradation at every step: MCP unavailable, RAG unavailable, AI unavailable — deterministic risk score always preserved
- `_build_degraded_explanation()` — structured fallback with all required labels and disclaimer, no AI needed
- `_build_safe_fallback()` — replacement explanation when AI output violated policy
- `_ensure_disclaimer()` — always appends teacher-determination disclaimer if AI omitted it
- `explain.py` upgraded — `POST /explain/full` fully orchestrated endpoint + `POST /explain` simple endpoint, both with `ExplainResponse` integrity labels (`has_evidence_label`, `has_disclaimer`, etc.)
- 57 Phase 8 tests — all passing

---

## Next Phase

**Phase 9 — Teacher Dashboard**

React dashboard: sessions list, risk indicators, evidence timeline, incident review, AI explanation panel, provider health, policy references.

---

## How Detection Works

The detection system uses multiple correlated signals — no single signal is treated as proof:

1. **Focus/blur events** — student left the exam window
2. **Tab switch detection** — student switched browser tabs
3. **Navigation signals** — browser navigated away from exam domain
4. **Copy/paste sequences** — large paste events, especially after external navigation
5. **AI domain signals** — navigation to or referrer from known AI assistant domains
6. **Keyboard shortcut patterns** — common AI-assistant activation shortcuts
7. **Rapid answer modification** — answer changed significantly in a short time window
8. **Behavioral sequences** — correlated chains of the above events

---

## AI Assistant Detection

The system implements observable detection signals for the following AI assistants:

| Assistant | Primary Domain | Status |
|-----------|---------------|--------|
| **ParakeetAI** | `parakeet-ai.com` | 🎯 PRIMARY TARGET |
| ChatGPT | `chat.openai.com` | Configured |
| Claude | `claude.ai` | Configured |
| Gemini | `gemini.google.com` | Configured |
| Microsoft Copilot | `copilot.microsoft.com` | Configured |
| Perplexity | `perplexity.ai` | Configured |

### Detection States

| State | Meaning |
|-------|---------|
| `DETECTED` | Observable signals strongly associated with AI assistant use |
| `SUSPECTED` | Behavioral patterns consistent with AI assistant use; insufficient for certainty |
| `NOT_DETECTED` | No observable signals detected |
| `UNOBSERVABLE` | The activity cannot be observed by available browser APIs |

### ParakeetAI Note

ParakeetAI (`parakeet-ai.com`) is specifically designed to operate without triggering standard proctoring detection. The system implements defense in depth:
- Direct domain navigation signals
- Subdomain variants (`www.`, `app.`, etc.)
- Navigation referrer analysis where available
- Behavioral sequence correlation
- Copy/paste timing analysis

**Absence of a DETECTED signal does NOT prove ParakeetAI was not used.**

---

## MCP Architecture

The MCP (Model Context Protocol) server runs as a dedicated Docker container and exposes structured tools consumed by the FastAPI backend:

```
MCP Tools:
  check_focus_loss          check_tab_switch
  check_copy                check_paste
  check_navigation          check_fullscreen
  check_keyboard_shortcuts  check_devtools_signal
  check_ai_assistant_signal correlate_behavior
  calculate_risk            get_exam_rules
  get_policy                get_student_timeline
  create_incident_summary
```

---

## Rules Engine

The behavioral rules engine is **fully deterministic** — LLMs do not influence numerical risk scores.

### Default Scoring Weights (configurable)

| Event | Score |
|-------|-------|
| TAB_SWITCH | +10 |
| FOCUS_LOSS | +5 |
| COPY | +15 |
| PASTE | +15 |
| FULLSCREEN_EXIT | +10 |
| SUSPICIOUS_NAVIGATION | +20 |
| AI_ASSISTANT_SIGNAL | +25 |
| REPEATED_VIOLATIONS | +20 |
| SUSPICIOUS_SEQUENCE | +20 |

### Risk States

| Score | State |
|-------|-------|
| 0–19 | NORMAL |
| 20–39 | MONITORING |
| 40–59 | ATTENTION |
| 60–79 | REVIEW_REQUIRED |
| 80–100 | HIGH_PRIORITY_REVIEW |

---

## RAG Architecture

The RAG system retrieves relevant policy documents to ground AI explanations:

- Exam rules
- Institution academic integrity policy
- AI assistance policy
- Allowed/prohibited resources
- Review procedures
- Incident handling guidance

**RAG does NOT invent policies.** Every AI explanation distinguishes:
- `OBSERVED EVIDENCE` — what the system actually recorded
- `POLICY INTERPRETATION` — what the retrieved policy says
- `AI INFERENCE` — what the AI model is inferring

### RAG Components

```
rag/
├── config.py                 # RAGConfig from env vars
├── server.py                 # FastAPI: /health /ingest /retrieve /policy-context
├── core/
│   ├── models.py             # Document, Chunk, RetrievedChunk, DocType
│   ├── chunker.py            # Sliding-window chunker with overlap
│   ├── vector_store.py       # InMemoryVectorStore + ChromaVectorStore + TF-IDF fallback
│   ├── rag_engine.py         # RAGEngine — ingest/retrieve/policy_context
│   └── document_loader.py    # Sample policy documents
└── tests/
    └── test_phase6.py        # 88 tests — all passing
```

### Document Types

| DocType | Purpose |
|---------|---------|
| `exam_rules` | Per-exam rules and restrictions |
| `institution_policy` | Institution-wide academic integrity |
| `ai_policy` | AI assistant prohibition policy |
| `allowed_resources` | What students may use |
| `prohibited_resources` | What is explicitly prohibited |
| `review_procedures` | How incidents are reviewed |
| `incident_guidance` | Handling confirmed incidents |
| `detection_explanation` | How detection works (for teachers) |
| `example_case` | Anonymized precedent cases |
| `other` | General documents |

### Retrieval API

```
POST /retrieve
  { query, top_k, exam_id, institution, doc_type }
  → { query, results: [{ chunk_id, document_title, doc_type, content, score }], result_count }

POST /policy-context
  { exam_id, institution }
  → { policy_context, chunk_count }
  # Returns pre-formatted text for AI prompt injection.
  # Clearly labelled as RETRIEVED POLICY — not AI-generated.
```

---

## Groq / NVIDIA Failover

```
Request → Groq (PRIMARY)
            │
         Success? → Return response
            │
           No (timeout/429/5xx/quota/token limit/empty)
            │
            ▼
         NVIDIA NIM (FALLBACK)
            │
         Success? → Return response + log fallback
            │
           No
            │
            ▼
         Degraded response (deterministic rules still work)
```

Groq is automatically restored as PRIMARY when health checks pass.

---

## Database Schema

```sql
-- Core tables (Phase 2 implementation)
users, students, teachers, exams, exam_rules,
exam_sessions, events, risk_scores, incidents,
evidence, ai_provider_logs, rag_documents,
rag_chunks, audit_logs
```

See `backend/migrations/` for full schema (available after Phase 2).

---

## API Documentation

Available after Phase 2 at: `http://localhost:8000/docs`

---

## Browser Extension Setup

See `extension/README.md` (available after Phase 3).

---

## Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd ai-exam-guardian

# 2. Copy environment template
cp .env.example .env
# Edit .env with your actual values

# 3. Start all services
docker-compose up --build

# 4. Access services
# Frontend:   http://localhost:3000
# Backend:    http://localhost:8000
# MCP:        http://localhost:8001
# Grafana:    http://localhost:3001
# Prometheus: http://localhost:9090
```

---

## Docker Setup

See `infra/` directory (available after Phase 1).

---

## Environment Variables

See [`.env.example`](.env.example) for all required environment variables.

**Never commit `.env` — it is in `.gitignore`.**

---

## Testing

```bash
# Root-level tests (pure logic — run natively)
python -m pytest tests/ -v

# Backend tests (requires Docker Python 3.11 for web-framework tests)
python -m pytest backend/tests/ --rootdir=backend -v

# MCP + Rules Engine tests
python -m pytest mcp/tests/test_phase4.py -v

# AI Assistant Detection tests
python -m pytest mcp/detectors/ai_assistant_detector/tests/test_phase5.py -v

# RAG tests
python -m pytest rag/tests/test_phase6.py -v

# Extension tests (Node.js)
node extension/tests/test_extension.mjs

# Run all Python tests at once
python -m pytest tests/ mcp/tests/ mcp/detectors/ai_assistant_detector/tests/ rag/tests/ -v
```

### Test Summary (as of Phase 7)

| Suite | Tests | Status |
|-------|-------|--------|
| Root Python tests | 9 | ✅ All pass |
| Backend Phase 2 tests | 9 pass + 7 skip | ✅ (skipped = Docker-only) |
| Backend Phase 7 tests | 56 pass + 3 skip | ✅ (skipped = Docker-only) |
| Backend Phase 8 tests | 57 | ✅ All pass |
| MCP Phase 4 tests | 50 | ✅ All pass |
| AI Detector Phase 5 tests | 50 | ✅ All pass |
| RAG Phase 6 tests | 88 | ✅ All pass |
| Extension JS tests | 37 | ✅ All pass |
| **TOTAL** | **319 pass / 0 fail** | ✅ |

---

## Security

- HTTPS via Nginx TLS termination
- JWT authentication with role-based authorization
- CORS restrictions per environment
- Rate limiting on all API endpoints
- Input validation (Pydantic models)
- Trivy CVE scanning in CI/CD
- Secure HTTP headers
- Audit logging
- No secrets in source code — environment variables only

See `docs/SECURITY.md` (available after Phase 10).

---

## AWS Deployment

See `infra/terraform/` (available after Phase 11).

---

## Terraform

See `infra/terraform/README.md` (available after Phase 11).

---

## CI/CD

GitHub Actions pipeline:
1. Lint
2. Test
3. Build
4. Trivy security scan
5. Docker build
6. ECR push
7. Deploy

See `.github/workflows/` (available after Phase 11).

---

## Monitoring

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001`

Dashboard panels:
- API Health, MCP Health, RAG Health
- Groq Health, NVIDIA Health
- Active Sessions, Review Required Count
- AI Detection Signals, Fallback Events

Available after Phase 10.

---

## Troubleshooting

See `docs/TROUBLESHOOTING.md` (available after Phase 12).

---

## Demo Scenario

Full end-to-end demo scenario available after Phase 12.

```
Student starts exam
    ↓ Normal behavior
    ↓ Focus lost (10:42:11)
    ↓ External navigation signal (10:42:18)
    ↓ Returned to exam (10:42:41)
    ↓ Copy event (10:42:45)
    ↓ Paste event (10:42:49)
    ↓ AI assistant signal (10:43:02)
    ↓ MCP correlates → risk score increases
    ↓ RAG retrieves exam policy
    ↓ Groq generates explanation (NVIDIA if Groq fails)
    ↓ Incident stored
    ↓ Teacher sees REVIEW REQUIRED
```

---

## Known Limitations

1. Browser-based telemetry is inherently limited — determined actors can circumvent it
2. ParakeetAI and similar tools are specifically designed to evade standard detection
3. Absence of detection signals does NOT prove innocence
4. This system provides evidence for human review — not automated verdicts
5. Extension permissions vary by browser version and enterprise policy
6. Desktop monitoring (Electron) provides stronger signals but requires consent
7. Network-level monitoring is not in scope for this MVP

---

## Future Enhancements

- EKS/Kubernetes deployment
- Desktop app with OS-level monitoring (consent-based)
- Additional AI assistant targets
- LMS integration (Canvas, Moodle, Blackboard)
- Camera-based proctoring integration (optional, consent-based)
- Network traffic analysis integration
- Federated behavioral models

---

## Progress Log

| Date | Phase | Work | Tests | Issues | Next |
|------|-------|------|-------|--------|------|
| 2025-01-01 | Phase 0 | Repository audit, architecture docs, rules, README | N/A (empty repo) | None — clean slate | Phase 1: Foundation |
| 2025-01-01 | Phase 1 | backend/ FastAPI base, frontend/ React base, extension/ Manifest V3, mcp/ server, rag/ engine, desktop/ Electron, infra/ Docker Compose + Nginx + Prometheus + Grafana, tests/ scaffold | 9 passed / 0 failed | Python 3.14 incompatible with pydantic-core — tests run standalone; Docker required for full stack | Phase 2: Database + FastAPI |
| 2025-01-01 | Phase 2 | FastAPI ORM models (14 tables), Pydantic schemas, auth/JWT, CRUD APIs, Alembic migrations, MySQL schema with CREATE DATABASE | 9 pass + 7 skip / 0 fail | pydantic-core no wheel on Python 3.14 — web-framework tests skipped (Docker only) | Phase 3: Browser Extension |
| 2025-01-01 | Phase 3 | Manifest V3 extension — background.js service worker, content.js telemetry, extensionBridge.js, popup UI, api.js flush client, constants.js config | 37 passed / 0 failed | schema.sql needed CREATE DATABASE + USE statements | Phase 4: MCP Server |
| 2025-01-01 | Phase 4 | MCP server — 15 tools (+ detect_ai_assistants = 16), deterministic RulesEngine, CorrelationEngine, configurable weights from env, create_incident_summary | 50 passed / 0 failed | None | Phase 5: AI Assistant Detection |
| 2025-01-01 | Phase 5 | AI Assistant Detector — 6 assistants (ParakeetAI first), DETECTED/SUSPECTED/NOT_DETECTED/UNOBSERVABLE states, 5 signal extractors, behavioral correlation, false-positive safeguards | 50 passed / 0 failed | None | Phase 6: RAG |
| 2025-01-01 | Phase 6 | RAG Knowledge System — RAGConfig, DocType (10 types), Chunker, InMemoryVectorStore+TF-IDF fallback, ChromaVectorStore, RAGEngine, 4 sample policy docs covering all 6 AI assistants, FastAPI server, rag_client.py | 88 passed / 0 failed | None | Phase 7: Groq + NVIDIA AI Gateway |
| 2025-01-01 | Phase 7 | AI Gateway — GatewayConfig, ProviderHealth state machine, ProviderClient (httpx), FallbackReason enum, AIGateway (3-level cascade), circuit breaker, automatic Groq recovery, LazyGateway singleton, explain.py API endpoint | 56 pass + 3 skip / 0 fail | Python 3.14 no auto event loop — used asyncio.new_event_loop() in tests | Phase 8: AI Explanation + RAG Integration |
| 2025-01-01 | Phase 8 | AI Explanation + RAG Integration — IncidentPrompt (build/validate), FORBIDDEN_PHRASES, ExplanationOrchestrator (MCP+RAG+AI pipeline), ExplanationResult.validate_output(), degraded/safe_fallback helpers, explain.py /full endpoint, integrity labels in response | 57 passed / 0 failed | None | Phase 9: Teacher Dashboard |

---

## Definition of Done

- [ ] React exam works
- [ ] Chrome/Edge extension works
- [ ] FastAPI works
- [ ] MySQL works
- [ ] MCP server works
- [ ] Rules Engine works
- [ ] AI Assistant Detector works
- [ ] ParakeetAI detection signals implemented
- [ ] ChatGPT detection signals implemented
- [ ] Claude detection signals implemented
- [ ] Gemini detection signals implemented
- [ ] Copilot detection signals implemented
- [ ] Perplexity detection signals implemented
- [x] RAG works
- [x] Groq works
- [x] NVIDIA fallback works
- [x] Automatic failover works
- [ ] Teacher dashboard works
- [ ] Evidence timeline works
- [ ] Risk scoring works
- [ ] Security controls work
- [ ] Tests pass
- [ ] Docker Compose works
- [ ] Terraform exists
- [ ] GitHub Actions works
- [ ] ECR workflow works
- [ ] Trivy scan works
- [ ] Prometheus works
- [ ] Grafana works
- [ ] README is complete
- [ ] Progress reaches 100%
- [ ] Final demo scenario passes
