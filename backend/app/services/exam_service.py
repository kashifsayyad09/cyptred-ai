"""Exam management service."""

from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam
from app.models.exam_rule import ExamRule
from app.models.teacher import Teacher
from app.schemas.exam import ExamCreate, ExamUpdate

logger = structlog.get_logger(__name__)


async def get_teacher_by_user_id(db: AsyncSession, user_id: str) -> Optional[Teacher]:
    result = await db.execute(select(Teacher).where(Teacher.user_id == user_id))
    return result.scalar_one_or_none()


async def create_exam(db: AsyncSession, teacher_id: str, data: ExamCreate) -> Exam:
    """Create an exam with default or provided rules."""
    exam = Exam(
        teacher_id=teacher_id,
        title=data.title,
        description=data.description,
        duration_minutes=data.duration_minutes,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        allow_resources=data.allow_resources,
    )
    db.add(exam)
    await db.flush()

    rule_kwargs = data.rules.model_dump() if data.rules else {}
    db.add(ExamRule(exam_id=exam.id, **rule_kwargs))

    logger.info("exam_created", exam_id=exam.id, teacher_id=teacher_id)
    return exam


async def list_exams_by_teacher(db: AsyncSession, teacher_id: str) -> List[Exam]:
    result = await db.execute(
        select(Exam).where(Exam.teacher_id == teacher_id).order_by(Exam.created_at.desc())
    )
    return list(result.scalars().all())


async def get_exam(db: AsyncSession, exam_id: str) -> Optional[Exam]:
    result = await db.execute(
        select(Exam).options(selectinload(Exam.rules)).where(Exam.id == exam_id)
    )
    return result.scalar_one_or_none()


async def update_exam(db: AsyncSession, exam: Exam, data: ExamUpdate) -> Exam:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(exam, field, value)
    logger.info("exam_updated", exam_id=exam.id)
    return exam
