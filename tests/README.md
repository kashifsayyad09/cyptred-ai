# AI Exam Guardian — Tests

## Structure

```
tests/
├── unit/           # Unit tests per service (added per phase)
├── integration/    # Cross-service integration tests
├── api/            # API contract tests
├── security/       # Security-focused tests
└── README.md
```

## Running Tests

```bash
# Backend tests
cd backend && python -m pytest

# MCP tests (Phase 4)
cd mcp && python -m pytest

# RAG tests (Phase 6)
cd rag && python -m pytest

# All tests via Docker
docker-compose -f infra/docker-compose.yml run backend python -m pytest
```

## Test Coverage by Phase

| Phase | Tests |
|-------|-------|
| 1 | Health endpoints |
| 2 | Auth, DB, exam/session APIs |
| 3 | Extension event capture |
| 4 | Rules Engine, MCP tools |
| 5 | AI Assistant Detector, false positive suite |
| 6 | RAG retrieval quality |
| 7 | AI Gateway failover |
| 8 | AI explanation generation |
| 9 | Dashboard API |
| 10 | Security controls |
| 11 | Deployment scripts |
| 12 | End-to-end demo scenario |
