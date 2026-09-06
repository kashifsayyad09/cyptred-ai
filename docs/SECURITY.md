# AI Exam Guardian — Security Documentation

> Full security documentation populated in Phase 10.

## Principles

- Minimal permissions (browser extension)
- API keys never exposed to client-side code
- All secrets via environment variables
- JWT authentication with role-based authorization
- CORS restrictions per environment
- Rate limiting on all endpoints
- Input validation (Pydantic)
- Trivy CVE scanning in CI/CD
- Secure HTTP headers
- Audit logging for all privileged actions
- Container security hardening

## Threat Model

Full threat model documented in Phase 10.
