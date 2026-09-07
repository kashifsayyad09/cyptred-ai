# AI Exam Guardian — Security Documentation

> **Version:** 0.1.0  
> **Last updated:** Phase 10 — Security + Observability

---

## Table of Contents

1. [Security Principles](#1-security-principles)
2. [Threat Model](#2-threat-model)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [API Security](#4-api-security)
5. [Secret Management](#5-secret-management)
6. [HTTP Security Headers](#6-http-security-headers)
7. [CORS Policy](#7-cors-policy)
8. [Rate Limiting](#8-rate-limiting)
9. [Input Validation](#9-input-validation)
10. [Container Security](#10-container-security)
11. [Dependency & CVE Scanning](#11-dependency--cve-scanning)
12. [Audit Logging](#12-audit-logging)
13. [Network Architecture](#13-network-architecture)
14. [Data Protection](#14-data-protection)
15. [AI Provider Security](#15-ai-provider-security)
16. [Browser Extension Security](#16-browser-extension-security)
17. [Incident Response](#17-incident-response)
18. [Security Controls Checklist](#18-security-controls-checklist)
19. [Known Limitations](#19-known-limitations)

---

## 1. Security Principles

| Principle | Implementation |
|-----------|---------------|
| **Least privilege** | Every component has only the permissions it needs |
| **Defence in depth** | Multiple independent controls at each layer |
| **Fail secure** | Service failures degrade gracefully — never expose data |
| **No client-side secrets** | API keys exist only on the server side |
| **Separation of concerns** | Frontend, backend, MCP, RAG are separate containers |
| **Audit everything** | All privileged actions are logged with request IDs |
| **Never accuse solely on one signal** | Risk scoring is deterministic and multi-signal |

---

## 2. Threat Model

### Assets to protect

| Asset | Sensitivity | Location |
|-------|-------------|----------|
| Groq API key | CRITICAL | Server environment only |
| NVIDIA API key | CRITICAL | Server environment only |
| JWT secret key | CRITICAL | Server environment only |
| Database credentials | CRITICAL | Server environment only |
| Student exam sessions | HIGH | MySQL (AWS RDS) |
| Exam content | HIGH | MySQL (AWS RDS) |
| Teacher access credentials | HIGH | MySQL (hashed) |
| Behavioral telemetry | MEDIUM | MySQL (AWS RDS) |
| AI explanation text | MEDIUM | MySQL (AWS RDS) |

### Threat actors

| Actor | Motivation | Mitigations |
|-------|-----------|-------------|
| **Student trying to cheat** | Avoid detection | Multi-signal correlation, extension monitoring, behavioral rules |
| **Student trying to disrupt exam** | Force session failure | Rate limiting, input validation, graceful degradation |
| **External attacker** | Exfiltrate student data | HTTPS, JWT auth, CORS, rate limiting, network isolation |
| **Malicious browser extension** | Inject false signals | Server-side validation, event schema enforcement |
| **API key theft** | Consume AI quota | Keys server-side only, never in JS bundles or headers |
| **Insider threat** | Access student data | RBAC, audit logs, role-based API restrictions |

### Attack surface

```
Internet
  │
  ▼
Nginx (port 80/443)
  ├── Rate limiting
  ├── Security headers
  ├── /metrics BLOCKED
  │
  ▼
FastAPI Backend (internal only)
  ├── JWT authentication
  ├── Role-based authorization
  ├── Pydantic input validation
  │
  ├──► MCP Server (internal Docker network only)
  ├──► RAG Engine (internal Docker network only)
  └──► MySQL RDS (private subnet, not publicly accessible)
```

---

## 3. Authentication & Authorization

### JWT Authentication

- All API endpoints (except `/health`, `/ready`, `/api/v1/auth/login`) require a valid JWT
- Tokens are signed with `HS256` using the `JWT_SECRET_KEY` environment variable
- Token expiry: configurable via `JWT_EXPIRE_MINUTES` (default: 60 minutes)
- Tokens contain: `user_id`, `role`, `exp`, `iat`

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| `teacher` | Read all sessions, exams, incidents, AI explanations |
| `student` | Submit events for own active session only |
| `admin` | All permissions + user management |

### Authorization enforcement

```python
# deps.py — used on every protected endpoint
def require_role(*roles: str) -> Callable:
    def dependency(current_user = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return dependency
```

---

## 4. API Security

### Endpoint security matrix

| Endpoint | Auth | Rate limit | Roles |
|----------|------|-----------|-------|
| `POST /api/v1/auth/login` | None | 10/min | — |
| `POST /api/v1/events` | JWT | 120/min | student |
| `GET /api/v1/sessions` | JWT | 60/min | teacher, admin |
| `POST /api/v1/explain` | JWT | 60/min | teacher, admin |
| `GET /health` | None | None | — |
| `GET /ready` | None | None | — |
| `GET /metrics` | **BLOCKED at Nginx** | — | — |

### Request ID tracing

Every request is assigned a `X-Request-ID` header (either echoed from the client or generated as UUID4). This ID propagates through all logs for full request tracing.

---

## 5. Secret Management

### Rules

1. **NEVER** commit secrets to version control
2. **NEVER** expose API keys in any client-side code (React, extension, Electron)
3. **NEVER** log API keys, JWT secrets, or database passwords
4. All secrets are loaded exclusively from environment variables

### Required secrets

See [`.env.example`](../.env.example) for the complete list of required variables. Every deployment must set:

- `APP_SECRET_KEY` — Flask/FastAPI application secret
- `JWT_SECRET_KEY` — JWT signing key (min 32 random bytes)
- `DB_PASSWORD` — MySQL database password
- `GROQ_API_KEY` — Groq API key (server-side only)
- `NVIDIA_API_KEY` — NVIDIA NIM API key (server-side only)
- `MCP_SECRET` — Internal MCP authentication token
- `GRAFANA_ADMIN_PASSWORD` — Grafana admin password

### Secret rotation

- Rotate `JWT_SECRET_KEY` periodically (invalidates all active sessions)
- Rotate AI provider keys if any compromise is suspected
- Use AWS Secrets Manager or similar for production deployments

---

## 6. HTTP Security Headers

Applied by `backend/app/middleware/security.py` on every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | camera=(), microphone=(), geolocation=() | Restrict browser APIs |
| `Content-Security-Policy` | `default-src 'none'` (API) / restrictive (docs) | Content injection prevention |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS (behind TLS) |
| `Cache-Control` | `no-store, no-cache, must-revalidate` | No caching of sensitive API responses |
| `X-Request-ID` | UUID4 per request | Request tracing |

Also applied at Nginx level in `infra/nginx/conf.d/locations.conf`.

---

## 7. CORS Policy

Configured in `backend/app/main.py`:

```python
CORSMiddleware(
    allow_origins=settings.CORS_ALLOWED_ORIGINS,  # from environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

- `CORS_ALLOWED_ORIGINS` must be set to exactly the frontend domains for production
- No wildcard (`*`) origins in production
- Example: `CORS_ALLOWED_ORIGINS=["https://examguardian.yourdomain.com"]`

---

## 8. Rate Limiting

Implemented at Nginx level (hardware-level, before FastAPI):

| Zone | Rate | Burst | Applies to |
|------|------|-------|-----------|
| `auth` | 10 req/min | 5 | `/api/v1/auth/` |
| `api` | 60 req/min | 20 | All other `/api/` |
| `events` | 120 req/min | 60 | `/api/v1/events` |

Over-limit requests receive `HTTP 429 Too Many Requests`.

---

## 9. Input Validation

All API request bodies are validated by **Pydantic v2** schemas in `backend/app/schemas/`.

- Unknown fields are rejected (`extra = "forbid"` on sensitive models)
- String fields have max-length constraints
- Enum fields enforce exact values
- Event types validated against `EventType` enum before DB insert

---

## 10. Container Security

### Dockerfile best practices

- Non-root user in all application containers
- Multi-stage builds where applicable (frontend)
- Pinned base image tags (not `:latest`)
- Minimal base images (`python:3.11-slim`, `node:20-alpine`)
- No secrets in `Dockerfile` or `docker-compose.yml` (environment variables only)

### Network isolation

- Internal services (MCP, RAG, MySQL) are NOT exposed on public ports
- Only Nginx ports 80/443 are exposed publicly
- Prometheus and Grafana are on non-standard ports (9090, 3001) — restrict at firewall in production
- `/metrics` endpoint is blocked at Nginx from public access

---

## 11. Dependency & CVE Scanning

### Trivy scanning

Trivy runs in CI for every pull request and push to `main`:

```yaml
# .github/workflows/ci.yml
- name: Trivy — filesystem scan (secrets + vulnerabilities)
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: fs
    severity: CRITICAL,HIGH
    format: sarif
    output: trivy-results.sarif
```

Results are uploaded to the **GitHub Security** tab as SARIF.

Docker images are also scanned after build.

### Suppression policy

See `.trivyignore`. CVEs are only suppressed with documented justification. No CRITICAL CVEs are suppressed without review.

---

## 12. Audit Logging

All privileged actions are logged with structured JSON via `structlog`:

- Authentication events (login success/failure)
- Role-based access denials
- Exam session lifecycle (start, end, abort)
- Risk score changes
- AI explanation requests
- Administrative actions

Log format (JSON):

```json
{
  "timestamp": "2024-01-15T10:31:04.123Z",
  "level": "info",
  "event": "login_success",
  "user_id": "usr_abc123",
  "role": "teacher",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ip": "10.0.1.5"
}
```

---

## 13. Network Architecture

```
[Internet]
     │ 80/443
     ▼
[Nginx] ─── blocks /metrics, /mcp/, /rag/
     │
     ├──► [Frontend :80] (internal)
     │
     └──► [Backend :8000] (internal)
               │
               ├──► [MCP :8001] (internal Docker network)
               ├──► [RAG :8002] (internal Docker network)
               └──► [MySQL RDS] (private subnet, VPC only)

[Prometheus :9090] ─► scrapes backend:8000/metrics (internal)
[Grafana :3001]    ─► queries Prometheus (internal)
```

In production on AWS:

- EC2 instances in a private subnet
- RDS in a separate private subnet with no public access
- Security groups restrict all inter-service traffic to minimum required ports
- Prometheus and Grafana are accessible only via VPN or bastion host

---

## 14. Data Protection

### Student data

- Behavioral telemetry is pseudonymised (student ID, not name, in event records)
- Raw events are stored with session context only
- No keystroke content is stored — only event type, timestamp, metadata
- No passwords, private messages, or unrelated browsing history are ever collected

### Exam content

- Exam questions stored in MySQL with access restricted to teacher/admin roles
- Students can only access questions for their currently active session

### Database

- Passwords stored as bcrypt hashes (never plaintext)
- All DB connections use TLS in production (`DB_SSL=true`)
- AWS RDS MySQL with automated backups enabled

---

## 15. AI Provider Security

### API key isolation

```
React/Extension ─── NO access to Groq/NVIDIA keys
Electron renderer ── NO access to Groq/NVIDIA keys
FastAPI backend ───► Groq/NVIDIA keys (environment variables only)
```

The AI Gateway runs exclusively in the FastAPI backend process. No client receives AI responses that include raw API credentials.

### Prompt injection defence

- All student-controlled content (exam answers, session metadata) is treated as data, not instructions
- System prompts use `FORBIDDEN_PHRASES` validation before sending to AI
- AI responses are validated — any response containing accusatory language is rejected and replaced with a safe fallback
- AI does NOT set numerical risk scores — those are deterministic from the Rules Engine

---

## 16. Browser Extension Security

The Chrome/Edge extension (`extension/`) follows Manifest V3 security model:

- **Minimum permissions requested** — only what exam integrity monitoring requires
- Consent and exam policy disclosed to the student before monitoring begins
- **Collected data:** focus/blur events, tab changes, copy/paste, fullscreen changes, navigation signals relevant to the current exam
- **Never collected:** passwords, form field content, private messages, unrelated browsing history
- All events sent to the backend API via HTTPS with JWT authentication
- Extension does NOT store session data locally beyond the active exam

---

## 17. Incident Response

If a security incident is suspected:

1. **Immediate:** Rotate all affected secrets (`JWT_SECRET_KEY`, AI provider keys, DB password)
2. **Audit logs:** Review structured logs for the affected time window
3. **Revoke sessions:** Delete active JWT sessions via DB if compromise is suspected
4. **Trivy scan:** Re-run Trivy against all images
5. **Notify:** Follow your institution's data breach notification policy
6. **Post-incident:** Document root cause, update `.trivyignore` only with justification

---

## 18. Security Controls Checklist

| Control | Status | Location |
|---------|--------|----------|
| HTTPS-ready configuration | ✅ | `infra/nginx/nginx.conf` |
| JWT authentication | ✅ | `backend/app/api/deps.py` |
| Role-based authorization | ✅ | `backend/app/api/deps.py` |
| CORS restrictions | ✅ | `backend/app/main.py` |
| Rate limiting | ✅ | `infra/nginx/conf.d/locations.conf` |
| Input validation (Pydantic) | ✅ | `backend/app/schemas/` |
| Security headers middleware | ✅ | `backend/app/middleware/security.py` |
| Security headers at Nginx | ✅ | `infra/nginx/conf.d/locations.conf` |
| /metrics blocked from public | ✅ | `infra/nginx/conf.d/locations.conf` |
| Structured audit logging | ✅ | `backend/app/core/logging.py` + structlog |
| Container non-root user | ✅ | All `Dockerfile`s |
| No secrets in source code | ✅ | `.env.example` only |
| `.env` in `.gitignore` | ✅ | `.gitignore` |
| Trivy CVE scanning | ✅ | `.github/workflows/ci.yml` |
| API keys server-side only | ✅ | `backend/app/core/config.py` |
| Prometheus metrics internal | ✅ | Docker network isolation |
| Grafana auth required | ✅ | `GF_SECURITY_ADMIN_*` env vars |

---

## 19. Known Limitations

| Limitation | Risk | Mitigation |
|-----------|------|-----------|
| JWT stored in localStorage (frontend) | XSS token theft | Strict CSP, httpOnly cookie migration planned |
| Rate limiting at Nginx only | Bypass if Nginx bypassed | VPC security groups restrict direct backend access |
| No IP-based geoblocking | — | Can be added with `ngx_http_geo_module` |
| Prometheus/Grafana no built-in auth | Internal exposure | Restrict via VPC / security groups in production |
| Electron app is unsigned | Code integrity | Document build signing requirements; not production-ready unsigned |
| Browser extension cannot detect all AI tools | Privacy/technical limits | Multi-signal correlation; limitation explicitly documented |

---

*This document is maintained alongside the codebase. Update this file whenever security controls are added, changed, or removed.*
