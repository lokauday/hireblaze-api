from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Resume(Base):
    """
    Resume model for storing user resumes.
    
    Stores resume title, content, and metadata.
    """
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Resume content (nullable for backward compatibility with existing data)
    title = Column(String, nullable=True)  # Will be populated from parsed_text or user input
    content = Column(Text, nullable=True)  # Full resume text content (can use parsed_text if available)
    
    # Legacy fields (kept for backward compatibility)
    original_file = Column(String, nullable=True)
    parsed_text = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="resumes")
    
    # Indexes
    __table_args__ = (
        Index('idx_resume_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Resume(id={self.id}, user_id={self.user_id}, title='{self.title}')>"
