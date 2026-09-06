"""Authentication service — registration, login, token validation."""

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.auth import RegisterRequest

logger = structlog.get_logger(__name__)


async def register_user(db: AsyncSession, req: RegisterRequest) -> User:
    """Create a new user with student or teacher profile. Raises ValueError on duplicate email."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise ValueError(f"Email already registered: {req.email}")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    await db.flush()  # get user.id before creating profile

    if req.role == "student":
        db.add(Student(user_id=user.id, full_name=req.full_name))
    elif req.role == "teacher":
        db.add(Teacher(user_id=user.id, full_name=req.full_name))

    logger.info("user_registered", user_id=user.id, role=req.role)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Verify credentials. Returns User on success, None on failure."""
    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        logger.warning("login_failed", email=email)
        return None
    logger.info("login_success", user_id=user.id, role=user.role)
    return user


def issue_token(user: User) -> dict:
    """Issue a JWT access token for the given user."""
    token = create_access_token(
        subject=user.id,
        extra={"role": user.role, "email": user.email},
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role, "user_id": user.id}
