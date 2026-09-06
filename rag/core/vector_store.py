"""
Vector store — wraps ChromaDB for embedding storage and similarity retrieval.

Uses sentence-transformers for embeddings.
Falls back to a lightweight in-memory store when ChromaDB is unavailable
(for unit tests and environments without GPU/heavy dependencies).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from rag.core.models import Chunk, RetrievedChunk, DocType
from rag.config import RAGConfig, load_config

logger = structlog.get_logger(__name__)


# ── In-memory fallback store (used in tests / no-chroma environments) ─────────

class InMemoryVectorStore:
    """
    Simple cosine-similarity store using sentence-transformers.
    No external service required — suitable for development and testing.
    """

    def __init__(self, embedding_model: str) -> None:
        self._model = None
        self._model_name = embedding_model
        self._chunks: list[tuple[Chunk, list[float]]] = []

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                logger.info("embedding_model_loaded", model=self._model_name)
            except ImportError:
                logger.warning("sentence_transformers_not_installed", fallback="tfidf")
                self._model = _TFIDFFallback()
        return self._model

    def add(self, chunks: list[Chunk]) -> None:
        model = self._get_model()
        for chunk in chunks:
            vec = model.encode(chunk.content).tolist()
            self._chunks.append((chunk, vec))

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        if not self._chunks:
            return []
        model = self._get_model()
        q_vec = model.encode(query).tolist()
        scored = [
            (chunk, _cosine(q_vec, vec))
            for chunk, vec in self._chunks
        ]
        # Apply metadata filters
        if filters:
            scored = [
                (c, s) for c, s in scored
                if _matches_filters(c, filters)
            ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self._chunks.clear()


# ── ChromaDB store (production) ───────────────────────────────────────────────

class ChromaVectorStore:
    """ChromaDB-backed vector store for production use."""

    def __init__(self, config: RAGConfig) -> None:
        self.config = config
        self._client = None
        self._collection = None
        self._model = None

    def _init(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            self._client = chromadb.PersistentClient(path=self.config.vector_store_path)
            self._collection = self._client.get_or_create_collection(
                name="exam_guardian_policies",
                metadata={"hnsw:space": "cosine"},
            )
            self._model = SentenceTransformer(self.config.embedding_model)
            logger.info("chroma_store_ready", path=self.config.vector_store_path)
        except ImportError as e:
            raise RuntimeError(f"ChromaDB/sentence-transformers not installed: {e}") from e

    def add(self, chunks: list[Chunk]) -> None:
        self._init()
        if not chunks:
            return
        texts = [c.content for c in chunks]
        embeddings = self._model.encode(texts).tolist()
        self._collection.add(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[c.metadata for c in chunks],
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        self._init()
        q_vec = self._model.encode(query).tolist()
        where = _build_chroma_filter(filters) if filters else None
        results = self._collection.query(
            query_embeddings=[q_vec],
            n_results=top_k,
            where=where,
        )
        chunks_and_scores = []
        for i, doc_id in enumerate(results["ids"][0]):
            meta     = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            score    = 1.0 - distance  # cosine distance → similarity
            chunk = Chunk(
                id=doc_id,
                document_id=meta.get("document_id", ""),
                chunk_index=int(meta.get("chunk_index", 0)),
                content=results["documents"][0][i],
                token_count=int(meta.get("token_count", 0)),
                metadata=meta,
                vector_id=doc_id,
            )
            chunks_and_scores.append((chunk, score))
        return chunks_and_scores

    def clear(self) -> None:
        if self._collection:
            self._collection.delete(where={"doc_type": {"$ne": "__never__"}})


# ── Factory ───────────────────────────────────────────────────────────────────

def get_vector_store(config: RAGConfig | None = None, use_chroma: bool = True):
    cfg = config or load_config()
    if use_chroma:
        try:
            store = ChromaVectorStore(cfg)
            store._init()
            return store
        except RuntimeError:
            logger.warning("chroma_unavailable_falling_back_to_memory")
    return InMemoryVectorStore(cfg.embedding_model)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = sum(x * x for x in a) ** 0.5
    nb  = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _matches_filters(chunk: Chunk, filters: dict[str, Any]) -> bool:
    for key, val in filters.items():
        if chunk.metadata.get(key) != val:
            return False
    return True


def _build_chroma_filter(filters: dict[str, Any]) -> dict | None:
    if not filters:
        return None
    if len(filters) == 1:
        k, v = next(iter(filters.items()))
        return {k: {"$eq": v}}
    return {"$and": [{k: {"$eq": v}} for k, v in filters.items()]}


# ── TF-IDF fallback (no sentence-transformers) ────────────────────────────────

class _TFIDFFallback:
    """Minimal bag-of-words fallback when sentence-transformers is unavailable."""

    def encode(self, text: str):
        import math
        words = text.lower().split()
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        # Return a simple normalized word-frequency vector as a list
        total = sum(freq.values()) or 1
        return _SparseVec({w: c / total for w, c in freq.items()})


class _SparseVec:
    def __init__(self, d: dict):
        self._d = d

    def tolist(self) -> list[float]:
        # Fixed 64-dim hash projection for cosine similarity
        vec = [0.0] * 64
        for word, weight in self._d.items():
            idx = hash(word) % 64
            vec[idx] += weight
        return vec
