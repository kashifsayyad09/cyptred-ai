"""Risk score endpoints — returns current risk state for a session."""

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.models.risk_score import RiskScore
from app.schemas.risk import RiskScoreResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/{session_id}/latest", response_model=RiskScoreResponse)
async def get_latest_risk(
    session_id: str, db: DB, current_user: CurrentUser
) -> RiskScoreResponse:
    """Get the most recent risk score for a session."""
    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.session_id == session_id)
        .order_by(RiskScore.calculated_at.desc())
        .limit(1)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk score found for this session",
        )
    return RiskScoreResponse.model_validate(score)
