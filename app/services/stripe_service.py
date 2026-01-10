"""
Stripe service for checkout, billing portal, and webhook handling.
"""
import logging
from typing import Optional
from datetime import datetime
import stripe
from app.core.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRICE_ID_PREMIUM,
    FRONTEND_URL
)

logger = logging.getLogger(__name__)

# Initialize Stripe client
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY not configured - Stripe features disabled")


def create_checkout_session(
    user_id: int,
    user_email: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None
) -> dict:
    """
    Create Stripe Checkout session for premium subscription.
    
    Args:
        user_id: User ID from database
        user_email: User email address
        success_url: Redirect URL after successful payment (defaults to FRONTEND_URL/dashboard?upgraded=1)
        cancel_url: Redirect URL if user cancels (defaults to FRONTEND_URL/pricing?cancelled=1)
    
    Returns:
        Dictionary with 'url' key containing checkout session URL
    """
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID_PREMIUM:
        raise ValueError("Stripe not configured - STRIPE_SECRET_KEY and STRIPE_PRICE_ID_PREMIUM required")
    
    if not success_url:
        success_url = f"{FRONTEND_URL}/dashboard?upgraded=1"
    if not cancel_url:
        cancel_url = f"{FRONTEND_URL}/pricing?cancelled=1"
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID_PREMIUM,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(user_id),
            },
            allow_promotion_codes=True,
        )
        
        logger.info(f"Created checkout session for user_id={user_id}, session_id={session.id}")
        return {'url': session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise ValueError(f"Failed to create checkout session: {str(e)}")


def create_billing_portal_session(
    customer_id: str,
    return_url: Optional[str] = None
) -> dict:
    """
    Create Stripe Billing Portal session for managing subscription.
    
    Args:
        customer_id: Stripe customer ID
        return_url: URL to return to after portal session (defaults to FRONTEND_URL/settings/billing)
    
    Returns:
        Dictionary with 'url' key containing portal session URL
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("Stripe not configured - STRIPE_SECRET_KEY required")
    
    if not return_url:
        return_url = f"{FRONTEND_URL}/settings/billing"
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        logger.info(f"Created billing portal session for customer_id={customer_id}")
        return {'url': session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating portal session: {e}")
        raise ValueError(f"Failed to create portal session: {str(e)}")


def verify_webhook(request_body: bytes, signature: str) -> dict:
    """
    Verify and parse Stripe webhook event.
    
    Args:
        request_body: Raw request body bytes
        signature: Stripe-Signature header value
    
    Returns:
        Parsed event dictionary
    
    Raises:
        ValueError: If webhook verification fails
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")
    
    try:
        event = stripe.Webhook.construct_event(
            request_body, signature, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Verified webhook event: {event['type']}, id={event['id']}")
        return event
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise ValueError(f"Invalid webhook payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise ValueError(f"Invalid signature: {e}")
