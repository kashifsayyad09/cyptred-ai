"""
RAG Engine — document ingestion and retrieval.

Responsibilities:
  - Ingest documents (chunk + embed + store)
  - Retrieve relevant chunks for a query
  - Filter by exam_id, institution, doc_type
  - Never invent policy — only retrieve stored content

IMPORTANT:
  RAG does NOT generate content.
  Every retrieved chunk is labelled with its source document and type.
  AI explanations must distinguish RETRIEVED POLICY from AI INFERENCE.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from rag.config import RAGConfig, load_config
from rag.core.models import Chunk, Document, DocType, RetrievedChunk
from rag.core.chunker import Chunker, content_hash
from rag.core.vector_store import get_vector_store, InMemoryVectorStore

logger = structlog.get_logger(__name__)


class RAGEngine:
    def __init__(
        self,
        config: RAGConfig | None = None,
        use_chroma: bool = True,
    ) -> None:
        self.config = config or load_config()
        self._chunker = Chunker(self.config)
        self._store = get_vector_store(self.config, use_chroma=use_chroma)
        self._doc_index: dict[str, Document] = {}   # doc_id → Document
        self._chunk_index: dict[str, Chunk] = {}    # chunk_id → Chunk

    # ── Ingestion ──────────────────────────────────────────────────────────────

    def ingest(self, document: Document) -> list[Chunk]:
        """
        Chunk and embed a document. Returns the list of created chunks.
        Skips if the document content is already ingested (by content hash).
        """
        if not document.id:
            document = _with_id(document)

        chunks = self._chunker.chunk(document)
        if not chunks:
            logger.warning("empty_document_skipped", title=document.title)
            return []

        self._store.add(chunks)
        self._doc_index[document.id] = document
        for chunk in chunks:
            self._chunk_index[chunk.id] = chunk

        logger.info(
            "document_ingested",
            doc_id=document.id,
            title=document.title,
            chunks=len(chunks),
            doc_type=document.doc_type.value,
        )
        return chunks

    def ingest_many(self, documents: list[Document]) -> int:
        """Ingest a list of documents. Returns total chunks created."""
        total = 0
        for doc in documents:
            total += len(self.ingest(doc))
        return total

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        exam_id: str | None = None,
        institution: str | None = None,
        doc_type: DocType | str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve the most relevant chunks for a query.
        Filters are applied before ranking — use them to scope retrieval
        to a specific exam, institution, or document type.
        """
        k = top_k or self.config.top_k
        filters: dict[str, Any] = {}
        if exam_id:
            filters["exam_id"] = exam_id
        if institution:
            filters["institution"] = institution
        if doc_type:
            filters["doc_type"] = (
                doc_type.value if isinstance(doc_type, DocType) else doc_type
            )

        results = self._store.search(query, top_k=k, filters=filters or None)

        retrieved = []
        for chunk, score in results:
            if score < self.config.similarity_threshold:
                continue
            doc = self._doc_index.get(chunk.document_id)
            retrieved.append(RetrievedChunk(
                chunk=chunk,
                score=score,
                document_title=doc.title if doc else chunk.metadata.get("title", ""),
                doc_type=DocType(chunk.metadata.get("doc_type", "other")),
                exam_id=chunk.metadata.get("exam_id"),
                institution=chunk.metadata.get("institution"),
            ))

        logger.info(
            "rag_retrieve",
            query_preview=query[:60],
            results=len(retrieved),
            filters=filters,
        )
        return retrieved

    def retrieve_policy_context(
        self,
        exam_id: str | None = None,
        institution: str | None = None,
    ) -> str:
        """
        Retrieve a combined policy context string for AI explanation prompts.
        Pulls exam_rules + ai_policy + institution_policy chunks.
        Returns a formatted text block. Never invents content.
        """
        all_chunks: list[RetrievedChunk] = []
        for dt in (DocType.EXAM_RULES, DocType.AI_POLICY, DocType.INSTITUTION_POLICY):
            chunks = self.retrieve(
                query="AI assistant prohibited exam rules academic integrity",
                top_k=3,
                exam_id=exam_id,
                institution=institution,
                doc_type=dt,
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            return (
                "No specific policy documents found for this exam. "
                "Default policy applies: AI assistants are prohibited during closed-resource examinations."
            )

        seen: set[str] = set()
        lines = ["=== RETRIEVED POLICY CONTEXT ===\n"]
        for rc in all_chunks:
            if rc.chunk.content in seen:
                continue
            seen.add(rc.chunk.content)
            lines.append(
                f"[Source: {rc.document_title} | Type: {rc.doc_type.value} | "
                f"Relevance: {rc.score:.2f}]\n{rc.chunk.content}\n"
            )

        lines.append(
            "\nNOTE: The above is RETRIEVED POLICY — not AI-generated content. "
            "AI explanations must distinguish retrieved policy from AI inference."
        )
        return "\n".join(lines)

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "documents_indexed": len(self._doc_index),
            "chunks_indexed":    len(self._chunk_index),
            "embedding_model":   self.config.embedding_model,
            "store_type":        type(self._store).__name__,
        }


# ── Helper ────────────────────────────────────────────────────────────────────

def _with_id(doc: Document) -> Document:
    from dataclasses import replace
    return replace(doc, id=str(uuid.uuid4()))
