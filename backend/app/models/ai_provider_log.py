"""AIProviderLog model — Groq/NVIDIA request audit trail."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIProviderLog(Base):
    __tablename__ = "ai_provider_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=lambda: str(uuid.uuid4()), index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("exam_sessions.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(
        Enum("groq", "nvidia", "none", name="ai_provider"),
        nullable=False, index=True,
    )
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(fsp=3), nullable=False, server_default=func.now(3), index=True
    )

    def __repr__(self) -> str:
        return f"<AIProviderLog provider={self.provider!r} success={self.success!r}>"
