"""Event ingestion service."""

from datetime import datetime, timezone
from typing import List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventIngest

logger = structlog.get_logger(__name__)


async def ingest_event(db: AsyncSession, data: EventIngest) -> Event:
    """Persist a telemetry event from the browser extension."""
    event = Event(
        session_id=data.session_id,
        event_type=data.event_type,
        occurred_at=data.occurred_at,
        received_at=datetime.now(timezone.utc),
        source=data.source,
        metadata_=data.metadata,
    )
    db.add(event)
    await db.flush()
    logger.info(
        "event_ingested",
        event_id=event.id,
        event_type=event.event_type,
        session_id=event.session_id,
    )
    return event


async def get_events_for_session(db: AsyncSession, session_id: str) -> List[Event]:
    result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.occurred_at.asc())
    )
    return list(result.scalars().all())


async def get_unprocessed_events(db: AsyncSession, session_id: str) -> List[Event]:
    result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id, Event.processed == False)  # noqa: E712
        .order_by(Event.occurred_at.asc())
    )
    return list(result.scalars().all())
