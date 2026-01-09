from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base


class UsageEvent(Base):
    """
    Usage event model for tracking AI feature usage.
    
    Tracks per-user, per-feature usage with month_key for fast monthly aggregation.
    """
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feature = Column(String, nullable=False, index=True)  # "ats_scan", "resume_tailor", "cover_letter", "jd_parse"
    amount = Column(Integer, default=1, nullable=False)  # credits consumed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    month_key = Column(String(7), nullable=False, index=True)  # "YYYY-MM" format for fast monthly queries

    # Composite index for fast monthly aggregation queries
    __table_args__ = (
        Index('idx_user_feature_month', 'user_id', 'feature', 'month_key'),
    )

    @staticmethod
    def get_month_key(date: datetime = None) -> str:
        """Generate month_key string in YYYY-MM format."""
        if date is None:
            date = datetime.utcnow()
        return date.strftime("%Y-%m")


# Backward compatibility alias
Usage = UsageEvent
