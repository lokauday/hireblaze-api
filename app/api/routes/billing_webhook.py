"""
Stripe webhook handler for subscription events.

Handles webhook events from Stripe to keep subscription state in sync.
"""
import logging
import stripe
from fastapi import APIRouter, Request, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from app.services.billing_service import (
    handle_checkout_session_completed,
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted
)
from app.services.billing_invoice_handlers import (
    handle_invoice_payment_succeeded,
    handle_invoice_payment_failed
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing Webhook"])

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def get_db():
    """Database session dependency with proper cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Handle Stripe webhook events.
    
    Verifies webhook signature and processes subscription-related events:
    - checkout.session.completed: Payment successful
    - customer.subscription.created: New subscription created
    - customer.subscription.updated: Subscription updated (plan change, renewal, etc.)
    - customer.subscription.deleted: Subscription canceled or expired
    
    Returns 200 OK to acknowledge receipt to Stripe.
    """
    # Get raw payload
    payload = await request.body()
    
    # Get database session
    db = SessionLocal()
    try:
        # Verify webhook signature
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured"
            )
        
        if not stripe_signature:
            logger.warning("Missing stripe-signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload in webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload: {str(e)}"
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid signature: {str(e)}"
            )
        
        # Process event based on type
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})
        
        logger.info(f"Processing webhook event: type={event_type}, id={event.get('id')}")
        
        try:
            if event_type == "checkout.session.completed":
                subscription = handle_checkout_session_completed(event_data, db)
                logger.info(f"Checkout completed: user_id={subscription.user_id}, plan={subscription.plan_type}")
                
            elif event_type == "customer.subscription.created":
                subscription = handle_subscription_created(event_data, db)
                logger.info(f"Subscription created: user_id={subscription.user_id}, plan={subscription.plan_type}")
                
            elif event_type == "customer.subscription.updated":
                subscription = handle_subscription_updated(event_data, db)
                logger.info(f"Subscription updated: user_id={subscription.user_id}, plan={subscription.plan_type}, status={subscription.status}")
                
            elif event_type == "customer.subscription.deleted":
                subscription = handle_subscription_deleted(event_data, db)
                logger.info(f"Subscription deleted: user_id={subscription.user_id}, downgraded to free")
                
            elif event_type == "invoice.payment_succeeded":
                handle_invoice_payment_succeeded(event_data, db)
                logger.info("Invoice payment succeeded")
                
            elif event_type == "invoice.payment_failed":
                handle_invoice_payment_failed(event_data, db)
                logger.warning("Invoice payment failed")
                
            else:
                # Unhandled event type - log but don't fail
                logger.debug(f"Unhandled webhook event type: {event_type}")
        
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {e}", exc_info=True)
            # Don't raise - we still want to return 200 to Stripe
            # Stripe will retry if needed
        
        # Always return success to Stripe
        return {"status": "success", "event_type": event_type}
        
    finally:
        db.close()
