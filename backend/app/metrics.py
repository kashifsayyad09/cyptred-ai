"""
Prometheus metrics registry for AI Exam Guardian backend.

All metrics are defined here and imported by:
  - The metrics middleware (request counts + latency)
  - Individual service layers (AI gateway, RAG, MCP calls)

Never expose raw metric names — always use these constants.
"""

from __future__ import annotations

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    REGISTRY,
    CollectorRegistry,
)

# ── Application info ──────────────────────────────────────────────────────────

APP_INFO = Info(
    "exam_guardian_app",
    "AI Exam Guardian application metadata",
)
APP_INFO.info({"version": "0.1.0", "service": "backend"})

# ── HTTP request metrics ──────────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "exam_guardian_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_LATENCY = Histogram(
    "exam_guardian_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "exam_guardian_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "path"],
)

# ── Event ingestion metrics ───────────────────────────────────────────────────

EVENTS_INGESTED_TOTAL = Counter(
    "exam_guardian_events_ingested_total",
    "Total exam telemetry events ingested",
    ["event_type"],
)

# ── Risk evaluation metrics ───────────────────────────────────────────────────

RISK_EVALUATIONS_TOTAL = Counter(
    "exam_guardian_risk_evaluations_total",
    "Total risk evaluations performed",
    ["risk_level"],
)

RISK_SCORE_HISTOGRAM = Histogram(
    "exam_guardian_risk_score",
    "Distribution of risk scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

ACTIVE_SESSIONS = Gauge(
    "exam_guardian_active_sessions",
    "Number of currently active exam sessions",
)

REVIEW_REQUIRED_COUNT = Gauge(
    "exam_guardian_review_required_sessions",
    "Sessions currently at REVIEW_REQUIRED or HIGH_PRIORITY_REVIEW",
)

# ── AI provider metrics ───────────────────────────────────────────────────────

AI_REQUESTS_TOTAL = Counter(
    "exam_guardian_ai_requests_total",
    "Total AI gateway requests",
    ["provider", "success"],
)

AI_FALLBACK_TOTAL = Counter(
    "exam_guardian_ai_fallback_total",
    "Total times NVIDIA fallback was activated",
)

AI_DEGRADED_TOTAL = Counter(
    "exam_guardian_ai_degraded_total",
    "Total times both providers failed (degraded response)",
)

AI_REQUEST_LATENCY = Histogram(
    "exam_guardian_ai_request_duration_seconds",
    "AI request latency in seconds",
    ["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ── RAG metrics ───────────────────────────────────────────────────────────────

RAG_RETRIEVAL_TOTAL = Counter(
    "exam_guardian_rag_retrievals_total",
    "Total RAG policy retrievals",
    ["success"],
)

RAG_RETRIEVAL_LATENCY = Histogram(
    "exam_guardian_rag_retrieval_duration_seconds",
    "RAG retrieval latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── MCP metrics ───────────────────────────────────────────────────────────────

MCP_TOOL_CALLS_TOTAL = Counter(
    "exam_guardian_mcp_tool_calls_total",
    "Total MCP tool invocations",
    ["tool", "success"],
)

MCP_TOOL_LATENCY = Histogram(
    "exam_guardian_mcp_tool_duration_seconds",
    "MCP tool call latency in seconds",
    ["tool"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0],
)

# ── AI detection metrics ──────────────────────────────────────────────────────

AI_DETECTION_SIGNALS_TOTAL = Counter(
    "exam_guardian_ai_detection_signals_total",
    "Total AI assistant detection signals",
    ["assistant", "state"],
)

# ── Database metrics ──────────────────────────────────────────────────────────

DB_QUERY_LATENCY = Histogram(
    "exam_guardian_db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)
