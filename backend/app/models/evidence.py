"""Evidence model — individual evidence items per incident."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(fsp=3), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="evidence_severity"),
        nullable=False, default="medium",
    )
    score_contribution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.500"))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    incident: Mapped["Incident"] = relationship("Incident", back_populates="evidence")

    def __repr__(self) -> str:
        return f"<Evidence id={self.id!r} type={self.evidence_type!r} severity={self.severity!r}>"
