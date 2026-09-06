"""
AI Exam Guardian — RAG Engine Server

Retrieves relevant exam and institution policy documents to ground AI explanations.

RAG does NOT generate content — it ONLY retrieves stored documents.
Every AI explanation that uses this server must distinguish:
  - RETRIEVED POLICY (from this server)
  - AI INFERENCE (from Groq/NVIDIA)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag.core.models import DocType
from rag.core.rag_engine import RAGEngine
from rag.core.document_loader import ALL_SAMPLE_DOCUMENTS

logger = structlog.get_logger(__name__)

# ── Singleton engine ──────────────────────────────────────────────────────────
_rag_engine: RAGEngine | None = None


def get_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine(use_chroma=False)  # in-memory for now; chroma in production
        # Pre-load sample documents
        count = _rag_engine.ingest_many(ALL_SAMPLE_DOCUMENTS)
        logger.info("rag_engine_ready", sample_docs=len(ALL_SAMPLE_DOCUMENTS), chunks=count)
    return _rag_engine


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "other"
    exam_id: Optional[str] = None
    institution: Optional[str] = None
    version: str = "1.0"


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    exam_id: Optional[str] = None
    institution: Optional[str] = None
    doc_type: Optional[str] = None


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    document_title: str
    doc_type: str
    content: str
    score: float
    exam_id: Optional[str]
    institution: Optional[str]


class RetrieveResponse(BaseModel):
    query: str
    results: list[RetrievedChunkResponse]
    result_count: int


class PolicyContextResponse(BaseModel):
    exam_id: Optional[str]
    institution: Optional[str]
    policy_context: str
    chunk_count: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    documents_indexed: int
    chunks_indexed: int
    store_type: str


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()   # warm up on startup
    yield


app = FastAPI(
    title="AI Exam Guardian RAG Engine",
    description=(
        "Policy document retrieval for grounded AI explanations. "
        "RAG does not generate content — it only retrieves stored documents."
    ),
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # internal service — Nginx restricts externally
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    engine = get_engine()
    s = engine.status()
    return HealthResponse(
        status="ok",
        service="rag-engine",
        version="0.6.0",
        documents_indexed=s["documents_indexed"],
        chunks_indexed=s["chunks_indexed"],
        store_type=s["store_type"],
    )


# ── Ingestion ─────────────────────────────────────────────────────────────────

@app.post("/ingest", tags=["Ingestion"])
async def ingest_document(req: IngestRequest) -> dict[str, Any]:
    """Ingest a policy document into the vector store."""
    import uuid
    from rag.core.models import Document

    try:
        doc_type = DocType(req.doc_type)
    except ValueError:
        doc_type = DocType.OTHER

    doc = Document(
        id=str(uuid.uuid4()),
        title=req.title,
        content=req.content,
        doc_type=doc_type,
        exam_id=req.exam_id,
        institution=req.institution,
        version=req.version,
    )
    engine = get_engine()
    chunks = engine.ingest(doc)
    return {
        "ok": True,
        "document_id": doc.id,
        "title": doc.title,
        "chunks_created": len(chunks),
    }


# ── Retrieval ─────────────────────────────────────────────────────────────────

@app.post("/retrieve", response_model=RetrieveResponse, tags=["Retrieval"])
async def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    """Retrieve the most relevant policy chunks for a query."""
    if not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query must not be empty",
        )

    engine = get_engine()
    doc_type = None
    if req.doc_type:
        try:
            doc_type = DocType(req.doc_type)
        except ValueError:
            pass

    results = engine.retrieve(
        query=req.query,
        top_k=req.top_k,
        exam_id=req.exam_id,
        institution=req.institution,
        doc_type=doc_type,
    )

    return RetrieveResponse(
        query=req.query,
        result_count=len(results),
        results=[
            RetrievedChunkResponse(
                chunk_id=r.chunk.id,
                document_title=r.document_title,
                doc_type=r.doc_type.value,
                content=r.chunk.content,
                score=round(r.score, 4),
                exam_id=r.exam_id,
                institution=r.institution,
            )
            for r in results
        ],
    )


@app.post("/policy-context", response_model=PolicyContextResponse, tags=["Retrieval"])
async def get_policy_context(
    exam_id: Optional[str] = None,
    institution: Optional[str] = None,
) -> PolicyContextResponse:
    """
    Retrieve a combined policy context string for AI explanation prompts.
    Returns formatted text that AI must use verbatim — not paraphrase or extend.
    """
    engine = get_engine()
    context = engine.retrieve_policy_context(exam_id=exam_id, institution=institution)
    chunks = engine.retrieve(
        query="AI assistant prohibited exam rules",
        top_k=10,
        exam_id=exam_id,
        institution=institution,
    )
    return PolicyContextResponse(
        exam_id=exam_id,
        institution=institution,
        policy_context=context,
        chunk_count=len(chunks),
    )


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("RAG_PORT", "8002")),
        reload=False,
        log_level="info",
    )
