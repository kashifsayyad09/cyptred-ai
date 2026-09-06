"""Exam session endpoints."""

from typing import List

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import DB, CurrentUser, TeacherOnly
from app.schemas.session import SessionCreate, SessionResponse
from app.services.session_service import (
    create_session,
    end_session,
    get_session,
    get_student_by_user_id,
    list_active_sessions_for_exam,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    data: SessionCreate, request: Request, db: DB, current_user: CurrentUser
) -> SessionResponse:
    """Student starts an exam session."""
    student = await get_student_by_user_id(db, current_user["sub"])
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    session = await create_session(
        db,
        exam_id=data.exam_id,
        student_id=student.id,
        ip_address=ip,
        user_agent=ua,
        extension_active=data.extension_active,
    )
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_endpoint(
    session_id: str, db: DB, current_user: CurrentUser
) -> SessionResponse:
    """Get session details."""
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session_endpoint(
    session_id: str, db: DB, current_user: CurrentUser
) -> SessionResponse:
    """End an active exam session."""
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session = await end_session(db, session)
    return SessionResponse.model_validate(session)


@router.get("/exam/{exam_id}/active", response_model=List[SessionResponse])
async def list_active_sessions(
    exam_id: str, db: DB, current_user: TeacherOnly
) -> List[SessionResponse]:
    """List all active sessions for an exam (teacher only)."""
    sessions = await list_active_sessions_for_exam(db, exam_id)
    return [SessionResponse.model_validate(s) for s in sessions]
