from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    plan_type = Column(String, default="free")  # free | pro | elite | recruiter
    status = Column(String, default="inactive")

    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
