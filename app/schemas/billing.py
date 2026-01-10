"""
Pydantic schemas for billing endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    """Request schema for creating checkout session."""
    plan: str = Field(..., description="Plan type: 'pro' or 'elite'", pattern="^(pro|elite)$")
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if payment is canceled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan": "pro",
                "success_url": "https://hireblaze.ai/dashboard?success=true",
                "cancel_url": "https://hireblaze.ai/pricing?canceled=true"
            }
        }


class CreateCheckoutSessionResponse(BaseModel):
    """Response schema for checkout session creation."""
    checkout_url: str = Field(..., description="Stripe checkout session URL")
    session_id: str = Field(..., description="Stripe checkout session ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
                "session_id": "cs_test_..."
            }
        }


class CreatePortalSessionRequest(BaseModel):
    """Request schema for creating portal session."""
    return_url: str = Field(..., description="URL to return to after portal session")
    
    class Config:
        json_schema_extra = {
            "example": {
                "return_url": "https://hireblaze.ai/dashboard"
            }
        }


class CreatePortalSessionResponse(BaseModel):
    """Response schema for portal session creation."""
    url: str = Field(..., description="Stripe customer portal URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://billing.stripe.com/p/session/..."
            }
        }


class BillingErrorResponse(BaseModel):
    """Error response schema for billing operations."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "billing_error",
                "detail": "Invalid plan type. Must be 'pro' or 'elite'."
            }
        }
