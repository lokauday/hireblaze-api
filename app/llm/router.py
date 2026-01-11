"""
Model router for selecting appropriate models based on feature and plan.
"""
import logging
from typing import Optional
from app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Model selection strategy
MODEL_ROUTING = {
    # Feature -> model mapping
    "job_match": "gpt-4o-mini",  # Cheap for simple analysis
    "recruiter_lens": "gpt-4o-mini",  # Cheap
    "interview_pack": "gpt-4o-mini",  # Cheap
    "outreach": "gpt-4o-mini",  # Cheap
    "transform": "gpt-4o-mini",  # Cheap
    "skill_gap": "gpt-4o-mini",  # Cheap
    "ats_map": "gpt-4o-mini",  # Cheap
    # Premium features can use better models
    "premium_analysis": "gpt-4o",  # Better model for premium users
}


def get_model_for_feature(feature: str, plan: str = "free") -> str:
    """
    Get appropriate model for a feature.
    
    Args:
        feature: Feature name (e.g., "job_match", "recruiter_lens")
        plan: User plan ("free" | "premium")
        
    Returns:
        Model identifier string
    """
    # Default to cheap model
    default_model = "gpt-4o-mini"
    
    # Get model from routing table
    model = MODEL_ROUTING.get(feature, default_model)
    
    # Premium users can get better models for premium features
    if plan == "premium" and feature.startswith("premium_"):
        model = MODEL_ROUTING.get("premium_analysis", model)
    
    return model


def is_model_available(model: str) -> bool:
    """Check if model is available (OpenAI configured)."""
    return bool(OPENAI_API_KEY)
