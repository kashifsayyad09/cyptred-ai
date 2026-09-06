# AI Exam Guardian — Bob Rules

## Project Identity
- Project: AI Exam Guardian
- Type: Privacy-first online exam integrity platform
- Mission: Detect and correlate suspicious exam-session behavior and potential unauthorized AI-assistant usage

## Core Constraints
- NEVER claim that browser-based systems detect cheating with 100% certainty
- NEVER accuse a student based on a single signal
- NEVER expose API keys (Groq, NVIDIA, AWS) to any client-side code
- NEVER commit .env files, secrets, or credentials
- NEVER use SQLite for production; use AWS RDS MySQL only
- NEVER use PostgreSQL; use MySQL only
- The final decision about a student ALWAYS belongs to the teacher/institution

## Development Rules
- Inspect existing files before modifying anything
- Prefer small, maintainable modules
- Write tests alongside implementation
- Use type hints in all Python code
- Validate all API inputs
- Handle all errors explicitly — never swallow exceptions silently
- Never hardcode configuration values; use environment variables
- Use meaningful names for all variables, functions, classes

## Phase Discipline
- Complete one phase fully before starting the next
- STOP after each phase and ask the user before continuing
- Update README.md progress after every phase
- Run tests after every phase
- Update TODO list after every phase

## AI Provider Rules
- Groq is PRIMARY; NVIDIA NIM is FALLBACK
- Implement automatic failover on: timeout, 429, 5xx, quota, token limit, connection error, empty response
- Restore Groq automatically when healthy
- The deterministic Rules Engine MUST work even when both AI providers are down
- Log: provider, request ID, failure reason, HTTP status, latency, fallback activation, timestamp

## Detection Rules
- AI assistant detection must return: DETECTED | SUSPECTED | NOT_DETECTED | UNOBSERVABLE
- Never claim absence of evidence proves software was not used
- Implement defense in depth for ParakeetAI detection (domain, behavioral, sequence correlation)
- Risk scores are deterministic — LLMs do NOT set numerical scores

## Security Rules
- HTTPS-ready configuration required
- JWT/session security required
- CORS restrictions required
- Rate limiting required
- Input validation on all endpoints
- Role-based authorization (teacher vs student)
- Trivy scanning in CI/CD
- Secure headers on all responses
- Audit logging for all privileged actions

## File/Folder Rules
- backend/     → FastAPI Python application
- frontend/    → React student exam + teacher dashboard
- extension/   → Manifest V3 Chrome/Edge extension
- mcp/         → MCP server container
- rag/         → RAG knowledge system
- desktop/     → Electron wrapper (future)
- infra/       → Terraform + Docker Compose + Nginx
- tests/       → All automated tests
- docs/        → Architecture and API documentation
