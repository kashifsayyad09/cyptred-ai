"""Event ingestion endpoint — receives telemetry from the browser extension."""

import structlog
from fastapi import APIRouter, HTTPException, status

from app.api.deps import DB, CurrentUser
from app.schemas.event import EventIngest, EventResponse
from app.services.event_service import ingest_event
from app.services.session_service import get_session

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event_endpoint(
    data: EventIngest, db: DB, current_user: CurrentUser
) -> EventResponse:
    """Accept a telemetry event from the browser extension."""
    session = await get_session(db, data.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not active (status={session.status})",
        )
    event = await ingest_event(db, data)
    return EventResponse.model_validate(event)
