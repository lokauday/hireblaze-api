from sqlalchemy import Column, Integer, String, ForeignKey, Date, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class AIUsage(Base):
    """
    Daily AI usage tracking for per-user, per-day limits.
    
    Tracks number of AI calls made by a user on a specific date.
    Used for enforcing daily limits for free users.
    """
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)  # YYYY-MM-DD format
    ai_calls_count = Column(Integer, default=0, nullable=False)

    # Unique constraint: one record per user per day
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_date'),
    )
