"""
Quota enforcement dependency for AI features.

This module provides require_quota() dependency that:
1. Authenticates the user
2. Checks current month usage against plan limits
3. Records usage if allowed
4. Raises HTTPException if quota exceeded
"""
import logging
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.auth_dependency import get_current_user
from app.services.quota_service import get_plan_for_user, check_and_consume
from app.db.models.usage import UsageEvent

logger = logging.getLogger(__name__)


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


def require_quota(feature: str, amount: int = 1):
    """
    Dependency that enforces quota limits before allowing feature usage.
    
    Args:
        feature: Feature name (e.g. "ats_scan", "resume_tailor", "cover_letter", "jd_parse")
        amount: Credits to consume (default: 1)
    
    Returns:
        User object if quota allows
        
    Raises:
        HTTPException 429: Quota exceeded with structured error detail
        HTTPException 401: Unauthorized
        HTTPException 404: User not found
    """
    def quota_checker(
        email: str = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Get user object
        user = get_user_from_email(email, db)
        
        # Get user's plan for error message
        plan_type = get_plan_for_user(db, user.id)
        
        # Check quota and consume atomically
        used, limit, remaining = check_and_consume(db, user.id, feature, amount)
        
        # Check if quota exceeded
        # If limit is not None and remaining is 0, verify if usage actually increased
        # (if it didn't increase, check_and_consume detected exceed and didn't record)
        if limit is not None and remaining == 0:
            # Verify: if used + amount would exceed limit, quota was exceeded
            # This means check_and_consume detected the exceed and didn't record usage
            if used + amount > limit:
                # Quota exceeded
                logger.warning(
                    f"Quota exceeded: user_id={user.id}, feature={feature}, "
                    f"plan={plan_type}, limit={limit}, used={used}"
                )
                
                # Raise HTTPException with structured error as specified
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "quota_exceeded",
                        "feature": feature,
                        "plan": plan_type,
                        "limit": limit,
                        "used": used,
                        "remaining": 0
                    }
                )
        
        # Success - usage already recorded by check_and_consume
        logger.debug(
            f"Quota check passed: user_id={user.id}, feature={feature}, "
            f"amount={amount}, plan={plan_type}, remaining={remaining if limit else 'unlimited'}"
        )
        
        return user
    
    return quota_checker
