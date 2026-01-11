"""
Resume Version model for tracking different resume versions per job.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)  # Optional: can be general or job-specific
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, index=True)  # Link to base resume if exists
    
    # Version metadata
    version = Column(Integer, nullable=False, default=1)  # Version number
    title = Column(String, nullable=False)  # e.g., "ATS Optimized", "For Google SWE"
    content = Column(Text, nullable=False)  # Resume content (markdown or text)
    
    # Version control
    is_active = Column(Boolean, default=False, nullable=False, index=True)  # Active version for this job
    is_base = Column(Boolean, default=False, nullable=False)  # Original/base version
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=True)  # "user" | "ai" | "auto"
    notes = Column(Text, nullable=True)  # User notes about this version
    
    # Relationships
    user = relationship("User", backref="resume_versions")
    job = relationship("Job", backref="resume_versions")
    
    __table_args__ = (
        Index('idx_user_job_active', 'user_id', 'job_id', 'is_active'),
        Index('idx_user_job_version', 'user_id', 'job_id', 'version'),
    )
    
    def __repr__(self):
        return f"<ResumeVersion(id={self.id}, job_id={self.job_id}, version={self.version}, title='{self.title}')>"
