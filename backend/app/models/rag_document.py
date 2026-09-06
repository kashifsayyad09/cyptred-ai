"""RAGDocument model — policy source documents."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(
        Enum(
            "exam_rules", "institution_policy", "ai_policy", "allowed_resources",
            "prohibited_resources", "review_procedures", "incident_guidance",
            "detection_explanation", "example_case", "other",
            name="rag_doc_type",
        ),
        nullable=False, default="other", index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["RAGChunk"]] = relationship(
        "RAGChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RAGDocument id={self.id!r} title={self.title!r} type={self.doc_type!r}>"
