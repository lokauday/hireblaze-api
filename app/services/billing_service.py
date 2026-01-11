"""
Billing service for Stripe integration.

Handles checkout sessions, customer portal, and webhook event processing.
"""
import logging
from typing import Optional, Dict, Tuple
import stripe
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.core.config import (
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_ID_PRO,
    STRIPE_PRICE_ID_ELITE,
    STRIPE_PRICE_ID_PREMIUM
)

logger = logging.getLogger(__name__)

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# Price ID to plan type mapping (built dynamically to handle None values)
def _build_price_mappings() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build price ID mappings from environment variables."""
    price_to_plan: Dict[str, str] = {}
    plan_to_price: Dict[str, str] = {}
    
    if STRIPE_PRICE_ID_PRO:
        price_to_plan[STRIPE_PRICE_ID_PRO] = "pro"
        plan_to_price["pro"] = STRIPE_PRICE_ID_PRO
    
    if STRIPE_PRICE_ID_ELITE:
        price_to_plan[STRIPE_PRICE_ID_ELITE] = "elite"
        plan_to_price["elite"] = STRIPE_PRICE_ID_ELITE
    
    # Add premium plan mapping
    from app.core.config import STRIPE_PRICE_ID_PREMIUM
    if STRIPE_PRICE_ID_PREMIUM:
        price_to_plan[STRIPE_PRICE_ID_PREMIUM] = "premium"
        plan_to_price["premium"] = STRIPE_PRICE_ID_PREMIUM
    
    return price_to_plan, plan_to_price

PRICE_ID_TO_PLAN, PLAN_TO_PRICE_ID = _build_price_mappings()


def get_plan_from_price_id(price_id: Optional[str]) -> Optional[str]:
    """Get plan type from Stripe price ID."""
    if not price_id:
        return None
    return PRICE_ID_TO_PLAN.get(price_id)


def get_price_id_from_plan(plan: str) -> Optional[str]:
    """Get Stripe price ID from plan type."""
    plan_lower = plan.lower()
    if plan_lower not in PLAN_TO_PRICE_ID:
        return None
    price_id = PLAN_TO_PRICE_ID[plan_lower]
    if not price_id or price_id.startswith("price_your_"):
        # Handle placeholder values from .env.example
        return None
    return price_id


def create_checkout_session(
    user: User,
    plan: str,
    success_url: str,
    cancel_url: str,
    db: Session
) -> stripe.checkout.Session:
    """
    Create a Stripe checkout session for subscription.
    
    Args:
        user: User object
        plan: Plan type (pro or elite)
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is canceled
        db: Database session
        
    Returns:
        Stripe checkout session object
    """
    price_id = get_price_id_from_plan(plan)
    if not price_id:
        raise ValueError(f"Invalid plan type: {plan}. Must be 'pro' or 'elite'")
    
    # Get or create Stripe customer
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    customer_id = None
    
    if subscription and subscription.stripe_customer_id:
        customer_id = subscription.stripe_customer_id
    else:
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)}
        )
        customer_id = customer.id
        
        # Update subscription record
        if not subscription:
            subscription = Subscription(user_id=user.id, plan_type="free", status="inactive")
            db.add(subscription)
        
        subscription.stripe_customer_id = customer_id
        db.commit()
    
    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": price_id,
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user.id),
            "plan": plan
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "plan": plan
            }
        }
    )
    
    logger.info(f"Created checkout session: session_id={session.id}, user_id={user.id}, plan={plan}")
    
    return session


def create_portal_session(user: User, return_url: str, db: Session) -> stripe.billing_portal.Session:
    """
    Create a Stripe customer portal session.
    
    Args:
        user: User object
        return_url: URL to return to after portal session
        db: Database session
        
    Returns:
        Stripe portal session object
    """
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    
    if not subscription or not subscription.stripe_customer_id:
        raise ValueError("User does not have an active Stripe customer ID")
    
    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )
    
    logger.info(f"Created portal session: session_id={session.id}, user_id={user.id}")
    
    return session


def handle_checkout_session_completed(event_data: Dict, db: Session) -> Subscription:
    """
    Handle checkout.session.completed webhook event.
    
    Args:
        event_data: Stripe event data object
        db: Database session
        
    Returns:
        Updated subscription object
    """
    session_data = event_data.get("object", {})
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")
    customer_email = session_data.get("customer_email")
    metadata = session_data.get("metadata", {})
    user_id_str = metadata.get("user_id")
    plan = metadata.get("plan")
    
    # Find user
    if user_id_str:
        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id).first()
    elif customer_email:
        user = db.query(User).filter(User.email == customer_email).first()
    else:
        raise ValueError("Cannot identify user from checkout session")
    
    if not user:
        raise ValueError(f"User not found for checkout session")
    
    # Get subscription
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    
    if not subscription:
        subscription = Subscription(user_id=user.id, plan_type="free", status="inactive")
        db.add(subscription)
    
    # Update subscription details
    subscription.stripe_customer_id = customer_id
    subscription.stripe_subscription_id = subscription_id
    subscription.status = "active"
    
    # Determine plan from price ID if not in metadata
    if not plan and subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            price_id = stripe_sub.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            plan = get_plan_from_price_id(price_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve subscription from Stripe: {e}")
    
    if plan:
        subscription.plan_type = plan
    
    # Get price ID and period end from subscription
    price_id = None
    period_end = None
    if subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            price_id = stripe_sub.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            period_end_timestamp = stripe_sub.get("current_period_end")
            if period_end_timestamp:
                from datetime import datetime
                period_end = datetime.fromtimestamp(period_end_timestamp)
            
            # Update plan from price ID if not set
            if not plan and price_id:
                plan = get_plan_from_price_id(price_id)
                if plan:
                    subscription.plan_type = plan
        except Exception as e:
            logger.warning(f"Failed to retrieve subscription from Stripe: {e}")
    
    subscription.stripe_price_id = price_id
    subscription.status = "active"
    
    # Sync to User model
    # Normalize plan: map "premium" to "pro", keep "pro" and "elite" as-is
    plan_type = subscription.plan_type
    if plan_type == "premium":
        plan_type = "pro"
    user.plan = plan_type if plan_type in ["free", "pro", "elite"] else "free"
    user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    user.stripe_price_id = price_id
    user.plan_status = "active"
    user.current_period_end = period_end
    
    db.commit()
    db.refresh(subscription)
    db.refresh(user)
    
    logger.info(f"Checkout completed: user_id={user.id}, plan={subscription.plan_type}, subscription_id={subscription_id}")
    logger.info(f"User upgraded: user_id={user.id}, plan={user.plan}, subscription_id={subscription_id}")
    
    return subscription


def handle_subscription_created(event_data: Dict, db: Session) -> Subscription:
    """
    Handle customer.subscription.created webhook event.
    
    Args:
        event_data: Stripe event data object
        db: Database session
        
    Returns:
        Updated subscription object
    """
    subscription_data = event_data.get("object", {})
    customer_id = subscription_data.get("customer")
    subscription_id = subscription_data.get("id")
    metadata = subscription_data.get("metadata", {})
    user_id_str = metadata.get("user_id")
    
    # Find user by customer_id
    subscription_record = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    
    if not subscription_record and user_id_str:
        user_id = int(user_id_str)
        subscription_record = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    if not subscription_record:
        raise ValueError(f"Subscription record not found for customer_id={customer_id}")
    
    # Update subscription
    subscription_record.stripe_subscription_id = subscription_id
    subscription_record.status = "active"
    
    # Get price ID, plan, and period end
    price_id = subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
    period_end_timestamp = subscription_data.get("current_period_end")
    period_end = None
    if period_end_timestamp:
        from datetime import datetime
        period_end = datetime.fromtimestamp(period_end_timestamp)
    
    if price_id:
        subscription_record.stripe_price_id = price_id
        plan = get_plan_from_price_id(price_id)
        if plan:
            subscription_record.plan_type = plan
    
    # Sync to User model
    user = db.query(User).filter(User.id == subscription_record.user_id).first()
    if user:
        user.plan = subscription_record.plan_type if subscription_record.plan_type in ["free", "premium"] else "premium"
        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.stripe_price_id = price_id
        user.plan_status = "active"
        user.current_period_end = period_end
    
    db.commit()
    db.refresh(subscription_record)
    
    logger.info(f"Subscription created: user_id={subscription_record.user_id}, plan={subscription_record.plan_type}, subscription_id={subscription_id}")
    if user:
        logger.info(f"User upgraded: user_id={user.id}, plan={user.plan}")
    
    return subscription_record


def handle_subscription_updated(event_data: Dict, db: Session) -> Subscription:
    """
    Handle customer.subscription.updated webhook event.
    
    Args:
        event_data: Stripe event data object
        db: Database session
        
    Returns:
        Updated subscription object
    """
    subscription_data = event_data.get("object", {})
    subscription_id = subscription_data.get("id")
    status = subscription_data.get("status")
    
    # Find subscription by stripe_subscription_id
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        raise ValueError(f"Subscription not found for subscription_id={subscription_id}")
    
    # Update status
    subscription.status = status
    
    # Get price ID and period end
    price_id = subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
    period_end_timestamp = subscription_data.get("current_period_end")
    period_end = None
    if period_end_timestamp:
        from datetime import datetime
        period_end = datetime.fromtimestamp(period_end_timestamp)
    
    if price_id:
        subscription.stripe_price_id = price_id
        plan = get_plan_from_price_id(price_id)
        if plan:
            subscription.plan_type = plan
    
    # Sync to User model
    user = db.query(User).filter(User.id == subscription.user_id).first()
    if user:
        # Normalize plan: map "premium" to "pro", keep "pro" and "elite" as-is
        plan_type = subscription.plan_type
        if plan_type == "premium":
            plan_type = "pro"
        user.plan = plan_type if plan_type in ["free", "pro", "elite"] else "free"
        user.plan_status = status
        user.current_period_end = period_end
        if price_id:
            user.stripe_price_id = price_id
    
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"Subscription updated: user_id={subscription.user_id}, status={status}, plan={subscription.plan_type}, subscription_id={subscription_id}")
    if user:
        logger.info(f"User plan updated: user_id={user.id}, plan={user.plan}, status={status}")
    
    return subscription


def handle_subscription_deleted(event_data: Dict, db: Session) -> Subscription:
    """
    Handle customer.subscription.deleted webhook event.
    Downgrades user to free plan.
    
    Args:
        event_data: Stripe event data object
        db: Database session
        
    Returns:
        Updated subscription object
    """
    subscription_data = event_data.get("object", {})
    subscription_id = subscription_data.get("id")
    
    # Find subscription by stripe_subscription_id
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        raise ValueError(f"Subscription not found for subscription_id={subscription_id}")
    
    # Downgrade to free immediately on cancellation
    subscription.plan_type = "free"
    subscription.status = "canceled"
    subscription.stripe_subscription_id = None  # Clear subscription ID but keep customer ID
    
    # Sync to User model - downgrade to free
    user = db.query(User).filter(User.id == subscription.user_id).first()
    if user:
        user.plan = "free"
        user.plan_status = "canceled"
        user.stripe_subscription_id = None
        # Keep customer_id and price_id for potential reactivation
    
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"Subscription deleted: user_id={subscription.user_id}, downgraded to free, subscription_id={subscription_id}")
    if user:
        logger.info(f"User downgraded: user_id={user.id}, plan={user.plan}")
    
    return subscription
