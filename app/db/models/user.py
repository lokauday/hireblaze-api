from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    visa_status = Column(String, default="Citizen")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Plan and subscription fields
    plan = Column(String, default="free", nullable=False)  # "free" | "premium"
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_price_id = Column(String, nullable=True)
    plan_status = Column(String, nullable=True)  # "active" | "canceled" | "past_due" | etc
    current_period_end = Column(DateTime(timezone=True), nullable=True)
