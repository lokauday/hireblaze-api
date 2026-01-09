"""
Plan-based usage limits configuration.

Single source of truth for monthly quota limits per plan.
None means unlimited quota for that feature.
"""
from typing import Dict, Optional, List

# Supported features
SUPPORTED_FEATURES: List[str] = [
    "ats_scan",
    "resume_tailor",
    "cover_letter",
    "jd_parse",
]

# Plan limits (per month)
PLAN_LIMITS: Dict[str, Dict[str, Optional[int]]] = {
    "free": {
        "ats_scan": 2,
        "resume_tailor": 3,
        "cover_letter": 3,
        "jd_parse": 5,
    },
    "pro": {
        "ats_scan": 20,
        "resume_tailor": 25,
        "cover_letter": 30,
        "jd_parse": 60,
    },
    "elite": {
        "ats_scan": None,  # Unlimited
        "resume_tailor": None,
        "cover_letter": None,
        "jd_parse": None,
    },
    "recruiter": {  # Same as elite
        "ats_scan": None,
        "resume_tailor": None,
        "cover_letter": None,
        "jd_parse": None,
    },
}


def get_plan_limit(plan_type: str, feature: str) -> Optional[int]:
    """
    Get the monthly limit for a feature in a given plan.
    
    Args:
        plan_type: Plan type (free, pro, elite, recruiter)
        feature: Feature name (ats_scan, resume_tailor, cover_letter, jd_parse)
        
    Returns:
        Monthly limit (int) or None for unlimited
    """
    plan_type = plan_type.lower() if plan_type else "free"
    limits = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])
    return limits.get(feature)


def has_unlimited_quota(plan_type: str, feature: str) -> bool:
    """Check if the plan has unlimited quota for a feature."""
    limit = get_plan_limit(plan_type, feature)
    return limit is None


def get_all_plan_limits(plan_type: str) -> Dict[str, Optional[int]]:
    """Get all limits for a plan type."""
    plan_type = plan_type.lower() if plan_type else "free"
    return PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])
