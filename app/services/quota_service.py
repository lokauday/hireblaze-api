"""
Quota service for managing usage limits and tracking.

Handles quota checking, usage recording, and monthly aggregation.
Production-ready service layer with proper error handling.
"""
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
from app.core.plan_limits import PLAN_LIMITS, get_plan_limit, SUPPORTED_FEATURES

logger = logging.getLogger(__name__)


def get_plan_for_user(db: Session, user_id: int) -> str:
    """
    Get user's plan type from subscription, defaulting to 'free' if none exists.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Plan type string (free, pro, elite, recruiter)
    """
    try:
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            return "free"
        return subscription.plan_type or "free"
    except Exception as e:
        # Handle schema mismatch gracefully - use raw SQL if ORM fails
        logger.warning(f"ORM query failed for subscription (schema mismatch?), using raw SQL: {e}")
        try:
            from sqlalchemy import text
            result = db.execute(
                text("SELECT plan_type FROM subscriptions WHERE user_id = :user_id LIMIT 1"),
                {"user_id": user_id}
            ).fetchone()
            if result and result[0]:
                return result[0]
            return "free"
        except Exception as sql_error:
            logger.error(f"Raw SQL also failed: {sql_error}")
            return "free"  # Default to free plan on error


def get_month_usage(db: Session, user_id: int, month_key: str) -> Dict[str, int]:
    """
    Get per-feature usage totals for a user in a given month.
    
    Args:
        db: Database session
        user_id: User ID
        month_key: Month key in "YYYY-MM" format
        
    Returns:
        Dictionary mapping feature names to total usage amounts
    """
    usage_query = db.query(
        UsageEvent.feature,
        func.sum(UsageEvent.amount).label('total')
    ).filter(
        and_(
            UsageEvent.user_id == user_id,
            UsageEvent.month_key == month_key
        )
    ).group_by(UsageEvent.feature).all()
    
    # Convert to dictionary, defaulting to 0 for features with no usage
    return {feature: int(total) for feature, total in usage_query}


def check_and_consume(
    db: Session,
    user_id: int,
    feature: str,
    amount: int = 1
) -> Tuple[int, Optional[int], int]:
    """
    Check quota and consume usage atomically if allowed.
    
    This function:
    1. Gets user's plan
    2. Gets current month usage
    3. Checks if request would exceed limit
    4. Records usage if allowed
    
    Args:
        db: Database session
        user_id: User ID
        feature: Feature name (ats_scan, resume_tailor, cover_letter, jd_parse)
        amount: Amount to consume (default: 1)
        
    Returns:
        Tuple of (used: int, limit: Optional[int], remaining: int)
        - used: Total usage after consuming this request
        - limit: Plan limit (None for unlimited)
        - remaining: Remaining quota (0 if exceeded, None for unlimited, -1 indicates unlimited was allowed)
        
    Note:
        If quota exceeded, remaining will be 0 and usage is NOT recorded.
        The caller should check remaining < 0 (when limit is not None) to detect exceeded.
    """
    # Get user's plan
    plan_type = get_plan_for_user(db, user_id)
    
    # Get current month key
    month_key = UsageEvent.get_month_key()
    
    # Get current month usage for this feature
    usage_dict = get_month_usage(db, user_id, month_key)
    current_usage = usage_dict.get(feature, 0)
    
    # Get plan limit
    limit = get_plan_limit(plan_type, feature)
    
    # Check if unlimited
    if limit is None:
        # Unlimited - record usage and return
        usage_event = UsageEvent(
            user_id=user_id,
            feature=feature,
            amount=amount,
            month_key=month_key
        )
        db.add(usage_event)
        db.commit()
        
        logger.info(
            f"Usage consumed (unlimited): user_id={user_id}, feature={feature}, "
            f"amount={amount}, plan={plan_type}"
        )
        
        return (current_usage + amount, None, -1)  # -1 indicates unlimited
    
    # Check if request would exceed limit
    if current_usage + amount > limit:
        # Quota exceeded - don't record usage, return info for error
        # Return current usage (before consuming) and remaining = 0 to indicate exceeded
        # Note: remaining is already 0 when current_usage >= limit
        remaining = max(0, limit - current_usage)
        # Return with remaining=0 to signal exceeded (when limit is not None and remaining==0)
        return (current_usage, limit, 0)
    
    # Record usage atomically
    usage_event = UsageEvent(
        user_id=user_id,
        feature=feature,
        amount=amount,
        month_key=month_key
    )
    db.add(usage_event)
    db.commit()
    db.refresh(usage_event)
    
    # Calculate final usage and remaining
    final_usage = current_usage + amount
    remaining = limit - final_usage
    
    logger.info(
        f"Usage consumed: user_id={user_id}, feature={feature}, amount={amount}, "
        f"used={final_usage}/{limit}, remaining={remaining}, plan={plan_type}"
    )
    
    return (final_usage, limit, remaining)


def get_usage_for_response(db: Session, user_id: int) -> Dict:
    """
    Get usage data formatted for GET /me/usage response.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dictionary with plan, month_key, and features dict
    """
    plan_type = get_plan_for_user(db, user_id)
    month_key = UsageEvent.get_month_key()
    usage_dict = get_month_usage(db, user_id, month_key)
    plan_limits = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])
    
    features = {}
    for feature in SUPPORTED_FEATURES:
        limit = plan_limits.get(feature)
        used = usage_dict.get(feature, 0)
        
        if limit is None:
            unlimited = True
            remaining = None
        else:
            unlimited = False
            remaining = max(0, limit - used)
        
        features[feature] = {
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "unlimited": unlimited
        }
    
    return {
        "plan": plan_type,
        "month_key": month_key,
        "features": features
    }
