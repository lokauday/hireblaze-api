"""
AI Memory model for storing per-user/per-job context.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.db.base import Base


class AiMemory(Base):
    __tablename__ = "ai_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)  # Optional job context
    key = Column(String, nullable=False)  # Memory key (e.g., "preferred_tone", "skills_focus")
    value_json = Column(JSON, nullable=False)  # Stored as JSON
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'job_id', 'key', name='uq_user_job_key'),
        Index('idx_user_job', 'user_id', 'job_id'),
        Index('idx_user_key', 'user_id', 'key'),
    )
