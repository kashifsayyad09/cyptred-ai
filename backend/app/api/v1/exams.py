"""Exam management endpoints — teacher only."""

from typing import List

import structlog
from fastapi import APIRouter, HTTPException, status

from app.api.deps import DB, TeacherOnly
from app.schemas.exam import ExamCreate, ExamResponse, ExamUpdate
from app.services.exam_service import (
    create_exam,
    get_exam,
    get_teacher_by_user_id,
    list_exams_by_teacher,
    update_exam,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam_endpoint(
    data: ExamCreate, db: DB, current_user: TeacherOnly
) -> ExamResponse:
    """Create a new exam."""
    teacher = await get_teacher_by_user_id(db, current_user["sub"])
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")
    exam = await create_exam(db, teacher.id, data)
    return ExamResponse.model_validate(exam)


@router.get("", response_model=List[ExamResponse])
async def list_exams(db: DB, current_user: TeacherOnly) -> List[ExamResponse]:
    """List all exams belonging to the current teacher."""
    teacher = await get_teacher_by_user_id(db, current_user["sub"])
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")
    exams = await list_exams_by_teacher(db, teacher.id)
    return [ExamResponse.model_validate(e) for e in exams]


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam_endpoint(exam_id: str, db: DB, current_user: TeacherOnly) -> ExamResponse:
    """Get a single exam by ID."""
    exam = await get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return ExamResponse.model_validate(exam)


@router.patch("/{exam_id}", response_model=ExamResponse)
async def update_exam_endpoint(
    exam_id: str, data: ExamUpdate, db: DB, current_user: TeacherOnly
) -> ExamResponse:
    """Update exam fields."""
    exam = await get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    exam = await update_exam(db, exam, data)
    return ExamResponse.model_validate(exam)
