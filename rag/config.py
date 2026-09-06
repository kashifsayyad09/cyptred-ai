"""
RAG Engine configuration — loaded from environment variables.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RAGConfig:
    embedding_model: str
    vector_store_path: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float


def load_config() -> RAGConfig:
    return RAGConfig(
        embedding_model=os.environ.get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        vector_store_path=os.environ.get("RAG_VECTOR_STORE_PATH", "./rag_vectorstore"),
        chunk_size=int(os.environ.get("RAG_CHUNK_SIZE", "512")),
        chunk_overlap=int(os.environ.get("RAG_CHUNK_OVERLAP", "64")),
        top_k=int(os.environ.get("RAG_TOP_K", "5")),
        similarity_threshold=float(os.environ.get("RAG_SIMILARITY_THRESHOLD", "0.3")),
    )
