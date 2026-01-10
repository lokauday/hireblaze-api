"""
InterviewPack model for storing interview preparation packs.
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class InterviewPack(Base):
    """
    InterviewPack model for storing AI-generated interview preparation materials.
    
    Stores questions, STAR outlines, 30/60/90 day plans, and other prep content.
    """
    __tablename__ = "interview_packs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=True, index=True)
    
    # Interview pack content (can be JSON or text)
    content = Column(JSON, nullable=False)  # Structured content: questions, STAR, plans, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="interview_packs")
    job_posting = relationship("JobPosting", backref="interview_packs")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_job_created', 'job_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<InterviewPack(id={self.id}, user_id={self.user_id}, job_id={self.job_id})>"
