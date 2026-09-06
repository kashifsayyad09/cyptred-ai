"""Exam model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "closed", "archived", name="exam_status"),
        nullable=False, default="draft", index=True,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    allow_resources: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="exams")
    rules: Mapped["ExamRule"] = relationship(
        "ExamRule", back_populates="exam", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["ExamSession"]] = relationship("ExamSession", back_populates="exam")

    def __repr__(self) -> str:
        return f"<Exam id={self.id!r} title={self.title!r} status={self.status!r}>"
