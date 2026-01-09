"""
Pydantic schemas for usage endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class FeatureUsageDetail(BaseModel):
    """Usage details for a single feature."""
    feature: str = Field(..., description="Feature name (ats_scan, resume_tailor, cover_letter, jd_parse)")
    limit: Optional[int] = Field(None, description="Monthly limit (None for unlimited)")
    used: int = Field(..., description="Current month usage")
    remaining: Optional[int] = Field(None, description="Remaining quota (None for unlimited)")
    unlimited: bool = Field(..., description="Whether this feature has unlimited quota")
    
    class Config:
        json_schema_extra = {
            "example": {
                "feature": "ats_scan",
                "limit": 20,
                "used": 5,
                "remaining": 15,
                "unlimited": False
            }
        }


class UsageSummary(BaseModel):
    """Summary statistics for usage."""
    total_features: int = Field(..., description="Total number of features")
    features_with_limits: int = Field(..., description="Number of features with limits")
    features_unlimited: int = Field(..., description="Number of unlimited features")


class UsageResponse(BaseModel):
    """Response schema for GET /me/usage."""
    plan: str = Field(..., description="Current plan type (free, pro, elite, recruiter)")
    month_key: str = Field(..., description="Current month in YYYY-MM format")
    features: List[FeatureUsageDetail] = Field(..., description="Per-feature usage details")
    summary: UsageSummary = Field(..., description="Usage summary statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan": "pro",
                "month_key": "2026-01",
                "features": [
                    {
                        "feature": "ats_scan",
                        "limit": 20,
                        "used": 5,
                        "remaining": 15,
                        "unlimited": False
                    },
                    {
                        "feature": "resume_tailor",
                        "limit": None,
                        "used": 0,
                        "remaining": None,
                        "unlimited": True
                    }
                ],
                "summary": {
                    "total_features": 4,
                    "features_with_limits": 3,
                    "features_unlimited": 1
                }
            }
        }


class QuotaExceededResponse(BaseModel):
    """Error response schema for quota exceeded."""
    error: str = Field("quota_exceeded", description="Error code")
    feature: str = Field(..., description="Feature that exceeded quota")
    plan: str = Field(..., description="User's current plan")
    limit: int = Field(..., description="Monthly limit for this feature")
    used: int = Field(..., description="Current month usage")
    remaining: int = Field(..., description="Remaining quota (0 if exceeded)")
    message: str = Field(..., description="Human-readable error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "quota_exceeded",
                "feature": "ats_scan",
                "plan": "free",
                "limit": 2,
                "used": 2,
                "remaining": 0,
                "message": "You have reached your monthly limit of 2 ats_scan requests. Upgrade your plan for more quota."
            }
        }
