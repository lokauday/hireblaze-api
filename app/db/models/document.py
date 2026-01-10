"""
Document model for AI Drive - stores resumes, cover letters, job descriptions, etc.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Document(Base):
    """
    Document model for AI Drive file/document management.
    
    Stores resumes, cover letters, job descriptions, and interview notes.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Document metadata
    title = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)  # "resume", "cover_letter", "job_description", "interview_notes"
    
    # Content
    content_text = Column(Text, nullable=True)  # Plain text or JSON string for rich content
    
    # Metadata
    tags = Column(JSON, nullable=True, default=list)  # List of tag strings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="documents")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_type_created', 'user_id', 'type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.type}')>"
