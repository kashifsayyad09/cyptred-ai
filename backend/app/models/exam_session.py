"""ExamSession model — one row per student attempt."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "completed", "flagged", "abandoned", name="session_status"),
        nullable=False, default="active", index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    extension_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="sessions")
    student: Mapped["Student"] = relationship("Student", back_populates="sessions")
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="session", cascade="all, delete-orphan"
    )
    risk_scores: Mapped[list["RiskScore"]] = relationship(
        "RiskScore", back_populates="session", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="session")

    def __repr__(self) -> str:
        return f"<ExamSession id={self.id!r} status={self.status!r}>"
