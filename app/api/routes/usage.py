"""
Usage tracking endpoints.

Provides usage statistics and quota information for authenticated users.
"""
import logging
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.auth_dependency import get_current_user
from app.services.quota_service import get_usage_for_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["Usage"])


def get_db():
    """Database session dependency following existing route patterns."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_email(email: str, db: Session) -> User:
    """Fetch User object from email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/usage", status_code=status.HTTP_200_OK)
def get_usage(
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current month usage statistics for the authenticated user.
    
    Returns:
    - plan: Current plan type (free, pro, elite, recruiter)
    - month_key: Current month in YYYY-MM format
    - features: Dictionary mapping feature names to usage details
        Each feature has: limit, used, remaining, unlimited
        
    Requires authentication via Bearer token.
    """
    # Get user
    user = get_user_from_email(email, db)
    
    # Get usage data
    usage_data = get_usage_for_response(db, user.id)
    
    logger.debug(f"Usage summary requested: user_id={user.id}, plan={usage_data['plan']}")
    
    return usage_data
