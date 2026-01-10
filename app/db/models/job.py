"""
Job-related models:
- Job: For tracking job applications (Job Tracker)
- JobDescription: For storing job description text content (JD parsing feature)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Job(Base):
    """
    Job model for tracking job applications.
    
    Stores company, title, status, notes, and application date.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Job details
    company = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    url = Column(String, nullable=True)  # Job posting URL
    
    # Status tracking
    status = Column(String, nullable=False, default="applied", index=True)  
    # Status values: "saved", "applied", "interviewing", "offer", "rejected", "withdrawn"
    
    # Notes and metadata
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)  # Date applied
    
    # Relationships
    user = relationship("User", backref="jobs")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_status_created', 'user_id', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, company='{self.company}', title='{self.title}', status='{self.status}')>"


class JobDescription(Base):
    """
    JobDescription model for storing job description text content.
    
    Used for JD parsing feature - stores the raw and parsed job description text.
    """
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Job description content
    original_file = Column(String, nullable=True)  # Original file path/URL if uploaded
    parsed_text = Column(Text, nullable=True)  # Parsed/processed job description text
    
    # Metadata
    title = Column(String, nullable=True)  # Job title if extracted
    company = Column(String, nullable=True)  # Company name if extracted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="job_descriptions")
    
    def __repr__(self):
        return f"<JobDescription(id={self.id}, title='{self.title}', company='{self.company}')>"
