"""Exam session service."""

from datetime import datetime, timezone
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_session import ExamSession
from app.models.student import Student

logger = structlog.get_logger(__name__)


async def get_student_by_user_id(db: AsyncSession, user_id: str) -> Optional[Student]:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    exam_id: str,
    student_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extension_active: bool = False,
) -> ExamSession:
    session = ExamSession(
        exam_id=exam_id,
        student_id=student_id,
        ip_address=ip_address,
        user_agent=user_agent,
        extension_active=extension_active,
    )
    db.add(session)
    await db.flush()
    logger.info("session_created", session_id=session.id, exam_id=exam_id, student_id=student_id)
    return session


async def get_session(db: AsyncSession, session_id: str) -> Optional[ExamSession]:
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    return result.scalar_one_or_none()


async def end_session(db: AsyncSession, session: ExamSession) -> ExamSession:
    session.ended_at = datetime.now(timezone.utc)
    session.status = "completed"
    logger.info("session_ended", session_id=session.id)
    return session


async def list_active_sessions_for_exam(db: AsyncSession, exam_id: str) -> List[ExamSession]:
    result = await db.execute(
        select(ExamSession)
        .where(ExamSession.exam_id == exam_id, ExamSession.status == "active")
        .order_by(ExamSession.started_at.desc())
    )
    return list(result.scalars().all())
