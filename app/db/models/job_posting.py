"""
JobPosting model for storing job postings with full JD text.
Separate from Job model which is for tracking applications.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class JobPosting(Base):
    """
    JobPosting model for storing job postings with full job description.
    
    Used for job match analysis and auto-tracking.
    """
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Job posting details
    source_url = Column(String, nullable=True)  # URL where job was found
    company = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    jd_text = Column(Text, nullable=False)  # Full job description text
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="job_postings")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_company_title', 'company', 'title'),
    )
    
    def __repr__(self):
        return f"<JobPosting(id={self.id}, company='{self.company}', title='{self.title}')>"
