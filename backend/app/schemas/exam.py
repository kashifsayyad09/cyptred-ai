"""Exam request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ExamRuleSchema(BaseModel):
    model_config = {"from_attributes": True}

    weight_tab_switch: int = 10
    weight_focus_loss: int = 5
    weight_copy: int = 15
    weight_paste: int = 15
    weight_fullscreen_exit: int = 10
    weight_suspicious_navigation: int = 20
    weight_ai_assistant_signal: int = 25
    weight_repeated_violations: int = 20
    weight_suspicious_sequence: int = 20
    fullscreen_required: bool = True
    ai_detection_enabled: bool = True


class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 60
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    allow_resources: bool = False
    rules: Optional[ExamRuleSchema] = None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 1 or v > 600:
            raise ValueError("duration_minutes must be between 1 and 600")
        return v


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    allow_resources: Optional[bool] = None


class ExamResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    teacher_id: str
    title: str
    description: Optional[str]
    duration_minutes: int
    status: str
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    allow_resources: bool
    created_at: datetime
    updated_at: datetime
