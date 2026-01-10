"""
MatchAnalysis model for storing resume-job match analysis results.
"""
from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class MatchAnalysis(Base):
    """
    MatchAnalysis model for storing AI-generated match analysis between resume and job.
    
    Stores match score, overlap analysis, missing skills, risks, improvement plan, and recruiter lens.
    """
    __tablename__ = "match_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=True, index=True)
    
    # Match score (0-100)
    score = Column(Float, nullable=False, index=True)  # Overall match score 0-100
    
    # JSON fields for structured analysis data
    overlap = Column(JSON, nullable=True)  # Skills/experiences that match
    missing = Column(JSON, nullable=True)  # Missing skills/requirements
    risks = Column(JSON, nullable=True)  # Risk factors/red flags
    improvement_plan = Column(JSON, nullable=True)  # Actionable improvement suggestions
    recruiter_lens = Column(JSON, nullable=True)  # Recruiter perspective analysis
    
    # Narrative text summary
    narrative = Column(Text, nullable=True)  # Human-readable narrative summary
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="match_analyses")
    resume = relationship("Resume", backref="match_analyses")
    job_posting = relationship("JobPosting", backref="match_analyses")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_score', 'user_id', 'score'),
        Index('idx_resume_job', 'resume_id', 'job_id'),
    )
    
    def __repr__(self):
        return f"<MatchAnalysis(id={self.id}, user_id={self.user_id}, score={self.score})>"
