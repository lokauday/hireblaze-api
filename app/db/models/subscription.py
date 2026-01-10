from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base


class Subscription(Base):
    """
    Subscription model for user billing plans.
    
    Tracks Stripe subscription details and plan type mapping.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    plan_type = Column(String, default="free", nullable=False)  # free | pro | elite | recruiter
    status = Column(String, default="inactive", nullable=False)  # active | inactive | canceled | past_due

    # Stripe integration fields
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_price_id = Column(String, nullable=True, index=True)  # Maps to plan_type (pro/elite price IDs)
