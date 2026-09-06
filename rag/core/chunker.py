"""
Document chunker — splits documents into overlapping text chunks.

Uses a simple character-based sliding window.
Token count is approximated as word count (no tokenizer dependency at this layer).
"""

from __future__ import annotations

import hashlib
import uuid

from rag.core.models import Chunk, Document
from rag.config import RAGConfig, load_config


class Chunker:
    def __init__(self, config: RAGConfig | None = None) -> None:
        self.config = config or load_config()

    def chunk(self, document: Document) -> list[Chunk]:
        """Split a document into overlapping chunks."""
        text   = document.content.strip()
        size   = self.config.chunk_size
        overlap = self.config.chunk_overlap
        chunks: list[Chunk] = []

        if not text:
            return chunks

        start = 0
        idx   = 0
        while start < len(text):
            end     = min(start + size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    chunk_index=idx,
                    content=content,
                    token_count=len(content.split()),
                    metadata={
                        "doc_type":    document.doc_type.value,
                        "exam_id":     document.exam_id,
                        "institution": document.institution,
                        "title":       document.title,
                        "version":     document.version,
                    },
                ))
                idx += 1
            if end == len(text):
                break
            start = end - overlap  # overlap window

        return chunks


def content_hash(text: str) -> str:
    """SHA-256 hash of document content for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
