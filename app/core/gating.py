"""
Feature gating and usage limit enforcement.

Handles plan-based feature access and daily usage limits for AI features.
"""
import logging
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models.user import User
from app.db.models.ai_usage import AIUsage
from app.core.config import MAX_FREE_AI_CALLS_PER_DAY

logger = logging.getLogger(__name__)


def get_user_plan(user: User) -> str:
    """
    Get user's plan type.
    
    Returns "free" or "premium" based on user.plan field.
    """
    return user.plan or "free"


def is_premium(user: User) -> bool:
    """Check if user has premium plan."""
    return get_user_plan(user) == "premium"


def get_today_ai_usage(db: Session, user_id: int) -> int:
    """Get today's AI usage count for a user."""
    today = date.today()
    usage = db.query(AIUsage).filter(
        AIUsage.user_id == user_id,
        AIUsage.date == today
    ).first()
    
    return usage.ai_calls_count if usage else 0


def increment_ai_usage(db: Session, user_id: int) -> None:
    """
    Increment today's AI usage count for a user.
    Creates record if it doesn't exist for today.
    """
    today = date.today()
    usage = db.query(AIUsage).filter(
        AIUsage.user_id == user_id,
        AIUsage.date == today
    ).first()
    
    if usage:
        usage.ai_calls_count += 1
    else:
        usage = AIUsage(
            user_id=user_id,
            date=today,
            ai_calls_count=1
        )
        db.add(usage)
    
    db.commit()
    logger.info(f"Incremented AI usage for user_id={user_id}, count={usage.ai_calls_count}")


def enforce_ai_limit(db: Session, user: User) -> None:
    """
    Enforce AI usage limits based on user plan.
    
    - Free users: limited to MAX_FREE_AI_CALLS_PER_DAY calls per day
    - Premium users: unlimited
    
    Raises HTTPException with 402/403 status if limit is reached.
    """
    plan = get_user_plan(user)
    
    # Premium users have unlimited access
    if plan == "premium":
        return
    
    # Free users: check daily limit
    today_count = get_today_ai_usage(db, user.id)
    
    if today_count >= MAX_FREE_AI_CALLS_PER_DAY:
        logger.warning(f"AI limit reached for free user_id={user.id}, count={today_count}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "detail": "Daily limit reached",
                "code": "LIMIT_REACHED",
                "limit": MAX_FREE_AI_CALLS_PER_DAY,
                "upgrade_required": True
            }
        )
    
    # Limit not reached, allow the request
    return
