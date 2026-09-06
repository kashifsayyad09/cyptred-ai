"""ExamSession request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    exam_id: str
    extension_active: bool = False


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    exam_id: str
    student_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    extension_active: bool
    created_at: datetime
