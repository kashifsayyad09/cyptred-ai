"""Event model — raw telemetry from the browser extension."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(fsp=3), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(fsp=3), nullable=False, server_default=func.now(3))
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="extension")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="events")

    def __repr__(self) -> str:
        return f"<Event id={self.id!r} type={self.event_type!r}>"
