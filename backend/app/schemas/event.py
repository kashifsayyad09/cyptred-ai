"""Event ingestion and response schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class EventIngest(BaseModel):
    session_id: str
    event_type: str
    occurred_at: datetime
    source: str = "extension"
    metadata: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    event_type: str
    occurred_at: datetime
    received_at: datetime
    source: str
    processed: bool
