"""FastAPI dependency helpers — auth, DB session, role guards."""

from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db

logger = structlog.get_logger(__name__)
bearer_scheme = HTTPBearer()


async def get_current_user_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    """Decode and validate the JWT. Returns the decoded payload."""
    try:
        return decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(*roles: str):
    """Dependency factory — enforces that the caller has one of the given roles."""
    async def _check(payload: Annotated[dict, Depends(get_current_user_payload)]) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return payload
    return _check


# Convenience type aliases
CurrentUser = Annotated[dict, Depends(get_current_user_payload)]
TeacherOnly = Annotated[dict, Depends(require_role("teacher", "admin"))]
StudentOnly = Annotated[dict, Depends(require_role("student"))]
DB = Annotated[AsyncSession, Depends(get_db)]
