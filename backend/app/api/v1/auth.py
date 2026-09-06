"""Authentication endpoints — register and login."""

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate_user, issue_token, register_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: DB) -> UserResponse:
    """Register a new student or teacher account."""
    try:
        user = await register_user(db, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: DB) -> TokenResponse:
    """Authenticate and receive a JWT access token."""
    user = await authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(**issue_token(user))
