"""
Feature gating and usage limit enforcement.

Handles plan-based feature access and daily usage limits for AI features.
Supports 3-tier plan system: free, pro, elite
"""
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models.user import User
from app.db.models.ai_usage import AIUsage
from app.core.config import MAX_FREE_AI_CALLS_PER_DAY, FRONTEND_URL

logger = logging.getLogger(__name__)


def get_user_plan(user: User) -> str:
    """
    Get user's plan type.
    
    Returns "free", "pro", or "elite" based on user.plan field.
    Defaults to "free" if not set.
    """
    plan = user.plan or "free"
    # Normalize legacy "premium" to "pro"
    if plan == "premium":
        return "pro"
    return plan


def is_premium(user: User) -> bool:
    """Check if user has premium plan (pro or elite)."""
    plan = get_user_plan(user)
    return plan in ["pro", "elite"]


def is_elite(user: User) -> bool:
    """Check if user has elite plan."""
    return get_user_plan(user) == "elite"


def has_feature_access(user: User, feature: str) -> bool:
    """
    Check if user has access to a specific feature based on their plan.
    
    Feature tiers:
    - free: Basic features only
    - pro: Most premium features
    - elite: All features
    """
    plan = get_user_plan(user)
    
    # Feature access matrix
    feature_tiers = {
        "free": [
            "basic_ai_rewrite",
            "grammar_check",
            "basic_job_tracking",
        ],
        "pro": [
            "basic_ai_rewrite",
            "grammar_check",
            "basic_job_tracking",
            "advanced_ai_tools",
            "interview_pack",
            "outreach_generator",
            "job_pack_export",
            "company_research",
            "resume_versioning",
            "ats_heatmap",
            "match_score",
            "recruiter_lens",
        ],
        "elite": [
            "basic_ai_rewrite",
            "grammar_check",
            "basic_job_tracking",
            "advanced_ai_tools",
            "interview_pack",
            "outreach_generator",
            "job_pack_export",
            "company_research",
            "resume_versioning",
            "ats_heatmap",
            "match_score",
            "recruiter_lens",
            "interview_simulation",
            "weekly_review",
            "smart_reapply",
        ],
    }
    
    # Check if feature is available in user's plan tier
    available_features = feature_tiers.get(plan, feature_tiers["free"])
    return feature in available_features


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
    - Pro/Elite users: unlimited
    
    Raises HTTPException with 402 status and structured payload if limit is reached.
    """
    plan = get_user_plan(user)
    
    # Pro and Elite users have unlimited access
    if plan in ["pro", "elite"]:
        return
    
    # Free users: check daily limit
    today_count = get_today_ai_usage(db, user.id)
    
    if today_count >= MAX_FREE_AI_CALLS_PER_DAY:
        logger.warning(f"AI limit reached for free user_id={user.id}, count={today_count}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "detail": "Daily limit reached. Upgrade to Pro or Elite for unlimited AI actions.",
                "code": "PAYWALL",
                "feature": "ai_actions",
                "upgrade_url": f"{FRONTEND_URL}/pricing",
                "limit": MAX_FREE_AI_CALLS_PER_DAY,
                "used": today_count,
            }
        )
    
    # Limit not reached, allow the request
    return


def enforce_feature_access(user: User, feature: str) -> None:
    """
    Enforce feature access based on user plan.
    
    Raises HTTPException with 402 status and structured payload if user doesn't have access.
    """
    if has_feature_access(user, feature):
        return
    
    plan = get_user_plan(user)
    required_plan = "pro" if feature not in ["interview_simulation", "weekly_review", "smart_reapply"] else "elite"
    
    logger.warning(f"Feature access denied: user_id={user.id}, plan={plan}, feature={feature}")
    
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "detail": f"This feature requires {required_plan.title()} plan. Upgrade to unlock.",
            "code": "PAYWALL",
            "feature": feature,
            "upgrade_url": f"{FRONTEND_URL}/pricing",
            "required_plan": required_plan,
        }
    )
