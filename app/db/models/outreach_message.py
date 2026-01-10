"""
OutreachMessage model for storing generated outreach messages.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class OutreachType(str, enum.Enum):
    """Types of outreach messages."""
    RECRUITER_FOLLOWUP = "recruiter_followup"
    LINKEDIN_DM = "linkedin_dm"
    THANK_YOU = "thank_you"
    REFERRAL_ASK = "referral_ask"


class OutreachMessage(Base):
    """
    OutreachMessage model for storing AI-generated outreach messages.
    
    Stores different types of outreach messages for job applications.
    """
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=True, index=True)
    
    # Message type and content
    type = Column(Enum(OutreachType), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Generated message content
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="outreach_messages")
    job_posting = relationship("JobPosting", backref="outreach_messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_type', 'user_id', 'type'),
        Index('idx_job_created', 'job_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<OutreachMessage(id={self.id}, user_id={self.user_id}, type='{self.type}')>"
