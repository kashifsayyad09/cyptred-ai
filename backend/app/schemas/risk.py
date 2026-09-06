"""Risk score response schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    score: int
    risk_level: str
    calculated_at: datetime
    contributing_events: Optional[Dict[str, Any]]
    notes: Optional[str]
