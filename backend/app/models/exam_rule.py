"""ExamRule model — per-exam configurable scoring weights."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExamRule(Base):
    __tablename__ = "exam_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exams.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Risk score weights — all configurable per exam
    weight_tab_switch: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    weight_focus_loss: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    weight_copy: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    weight_paste: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    weight_fullscreen_exit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    weight_suspicious_navigation: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    weight_ai_assistant_signal: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    weight_repeated_violations: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    weight_suspicious_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # Risk level thresholds
    threshold_monitoring: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    threshold_attention: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    threshold_review_required: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    threshold_high_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=80)

    # Feature flags
    fullscreen_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_detection_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="rules")

    def __repr__(self) -> str:
        return f"<ExamRule exam_id={self.exam_id!r}>"
