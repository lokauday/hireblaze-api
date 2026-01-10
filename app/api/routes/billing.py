"""
Billing endpoints for Stripe integration.

Handles checkout sessions and customer portal access.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.auth_dependency import get_current_user
from app.services.billing_service import (
    create_checkout_session,
    create_portal_session
)
from app.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    CreatePortalSessionRequest,
    CreatePortalSessionResponse,
    BillingErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_email(email: str, db: Session):
    """Fetch User object from email."""
    from app.db.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post(
    "/create-checkout-session",
    response_model=CreateCheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": BillingErrorResponse, "description": "Invalid request"},
        500: {"model": BillingErrorResponse, "description": "Billing service error"}
    }
)
def create_checkout(
    request: CreateCheckoutSessionRequest,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe checkout session for subscription upgrade.
    
    Creates a secure Stripe checkout session that allows users to upgrade
    to Pro or Elite plans. After successful payment, Stripe will send a
    webhook event to update the user's subscription.
    
    Requires authentication via Bearer token.
    """
    try:
        # Get user
        user = get_user_from_email(email, db)
        
        # Validate plan
        if request.plan.lower() not in ["pro", "elite"]:
            logger.warning(f"Invalid plan requested: {request.plan}, user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "billing_error",
                    "detail": "Invalid plan type. Must be 'pro' or 'elite'."
                }
            )
        
        # Create checkout session
        session = create_checkout_session(
            user=user,
            plan=request.plan.lower(),
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            db=db
        )
        
        logger.info(
            f"Checkout session created: session_id={session.id}, "
            f"user_id={user.id}, plan={request.plan}"
        )
        
        return CreateCheckoutSessionResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except ValueError as e:
        logger.error(f"ValueError creating checkout session: {e}, user_email={email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "billing_error",
                "detail": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}, user_email={email}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "billing_error",
                "detail": "Failed to create checkout session. Please try again later."
            }
        )


@router.post(
    "/create-portal-session",
    response_model=CreatePortalSessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": BillingErrorResponse, "description": "No active subscription"},
        404: {"model": BillingErrorResponse, "description": "User not found"},
        500: {"model": BillingErrorResponse, "description": "Billing service error"}
    }
)
def create_portal(
    request: CreatePortalSessionRequest,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe customer portal session.
    
    Allows users to manage their subscription, update payment methods,
    view invoices, and cancel subscriptions through Stripe's hosted
    customer portal.
    
    Requires authentication via Bearer token and an active subscription.
    """
    try:
        # Get user
        user = get_user_from_email(email, db)
        
        # Create portal session
        session = create_portal_session(
            user=user,
            return_url=request.return_url,
            db=db
        )
        
        logger.info(f"Portal session created: session_id={session.id}, user_id={user.id}")
        
        return CreatePortalSessionResponse(url=session.url)
        
    except ValueError as e:
        logger.warning(f"ValueError creating portal session: {e}, user_id={user.id if 'user' in locals() else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "billing_error",
                "detail": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Error creating portal session: {e}, user_email={email}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "billing_error",
                "detail": "Failed to create portal session. Please try again later."
            }
        )


@router.get("/status", status_code=status.HTTP_200_OK)
def billing_status():
    """Health check endpoint for billing service."""
    return {"status": "billing service active"}
