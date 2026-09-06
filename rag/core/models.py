"""
Document models for the RAG system.

Every document has:
  - content: the raw text
  - metadata: doc_type, exam_id, institution, title, version
  - chunks: produced by the chunker
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocType(str, Enum):
    EXAM_RULES            = "exam_rules"
    INSTITUTION_POLICY    = "institution_policy"
    AI_POLICY             = "ai_policy"
    ALLOWED_RESOURCES     = "allowed_resources"
    PROHIBITED_RESOURCES  = "prohibited_resources"
    REVIEW_PROCEDURES     = "review_procedures"
    INCIDENT_GUIDANCE     = "incident_guidance"
    DETECTION_EXPLANATION = "detection_explanation"
    EXAMPLE_CASE          = "example_case"
    OTHER                 = "other"


@dataclass
class Document:
    id: str
    title: str
    content: str
    doc_type: DocType
    exam_id: str | None = None
    institution: str | None = None
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    # Set after embedding
    vector_id: str | None = None


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float          # similarity score 0.0–1.0
    document_title: str
    doc_type: DocType
    exam_id: str | None
    institution: str | None
