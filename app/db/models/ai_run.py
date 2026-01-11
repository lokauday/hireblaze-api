"""
AI Run model for tracking LLM API calls.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Index
from sqlalchemy.sql import func
from app.db.base import Base


class AiRun(Base):
    __tablename__ = "ai_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feature = Column(String, nullable=False, index=True)  # e.g., "job_match", "recruiter_lens"
    input_hash = Column(String, index=True)  # Hash of input for deduplication
    prompt_version = Column(String, nullable=False)  # e.g., "match_v1"
    model = Column(String, nullable=False)  # e.g., "gpt-4o-mini"
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)  # Estimated cost in USD
    status = Column(String, nullable=False, default="pending")  # "pending", "completed", "failed"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_user_feature', 'user_id', 'feature'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )
