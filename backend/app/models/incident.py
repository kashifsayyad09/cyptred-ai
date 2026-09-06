"""Incident model — flagged sessions requiring teacher review."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    status: Mapped[str] = mapped_column(
        Enum("open", "under_review", "resolved", "dismissed", name="incident_status"),
        nullable=False, default="open", index=True,
    )
    risk_score_at_flag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level_at_flag: Mapped[str] = mapped_column(
        Enum(
            "NORMAL", "MONITORING", "ATTENTION", "REVIEW_REQUIRED", "HIGH_PRIORITY_REVIEW",
            name="incident_risk_level",
        ),
        nullable=False, default="NORMAL",
    )
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    teacher_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="incidents")
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id!r} status={self.status!r}>"
