"""RiskScore model — deterministic score snapshots from the Rules Engine."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(
        Enum(
            "NORMAL", "MONITORING", "ATTENTION", "REVIEW_REQUIRED", "HIGH_PRIORITY_REVIEW",
            name="risk_level",
        ),
        nullable=False, default="NORMAL", index=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(fsp=3), nullable=False, server_default=func.now(3), index=True
    )
    contributing_events: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="risk_scores")

    def __repr__(self) -> str:
        return f"<RiskScore session={self.session_id!r} score={self.score!r} level={self.risk_level!r}>"
