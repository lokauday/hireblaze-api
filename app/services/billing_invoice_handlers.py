"""
Invoice event handlers for Stripe webhooks.

Handles invoice.payment_succeeded and invoice.payment_failed events.
"""
import logging
from typing import Dict
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.subscription import Subscription

logger = logging.getLogger(__name__)


def handle_invoice_payment_succeeded(event_data: Dict, db: Session) -> None:
    """
    Handle invoice.payment_succeeded webhook event.
    
    Ensures subscription status remains active after successful payment.
    """
    invoice_data = event_data.get("object", {})
    customer_id = invoice_data.get("customer")
    subscription_id = invoice_data.get("subscription")
    
    if not subscription_id:
        logger.warning("invoice.payment_succeeded: No subscription ID in invoice")
        return
    
    # Find subscription
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        logger.warning(f"invoice.payment_succeeded: Subscription not found for subscription_id={subscription_id}")
        return
    
    # Ensure subscription is active
    subscription.status = "active"
    
    # Sync to User model
    user = db.query(User).filter(User.id == subscription.user_id).first()
    if user:
        user.plan_status = "active"
    
    db.commit()
    
    logger.info(f"Invoice payment succeeded: user_id={subscription.user_id}, subscription_id={subscription_id}")


def handle_invoice_payment_failed(event_data: Dict, db: Session) -> None:
    """
    Handle invoice.payment_failed webhook event.
    
    Updates subscription status to past_due.
    """
    invoice_data = event_data.get("object", {})
    customer_id = invoice_data.get("customer")
    subscription_id = invoice_data.get("subscription")
    
    if not subscription_id:
        logger.warning("invoice.payment_failed: No subscription ID in invoice")
        return
    
    # Find subscription
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        logger.warning(f"invoice.payment_failed: Subscription not found for subscription_id={subscription_id}")
        return
    
    # Update status to past_due
    subscription.status = "past_due"
    
    # Sync to User model
    user = db.query(User).filter(User.id == subscription.user_id).first()
    if user:
        user.plan_status = "past_due"
    
    db.commit()
    
    logger.warning(f"Invoice payment failed: user_id={subscription.user_id}, subscription_id={subscription_id}")
