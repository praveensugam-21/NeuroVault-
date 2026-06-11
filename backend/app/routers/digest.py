from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.security import SecurityService
from app.services.weekly_digest import WeeklyDigestService

router = APIRouter(prefix="/api/digest", tags=["Weekly Digest"])

@router.get("/weekly")
def get_weekly_digest(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the AI-generated weekly digest containing:
    - Expiry alerts (upcoming 30 days)
    - New connections made
    - trending topics
    - did you forget old files
    - knowledge scores
    - recommended next actions
    """
    digest_data = WeeklyDigestService.generate_digest(db, current_user.id)
    return digest_data
