"""
Company Pack model for storing company research packs per job.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class CompanyPack(Base):
    __tablename__ = "company_packs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Pack content (stored as JSON for flexibility)
    content_json = Column(JSON, nullable=False)  # Structured content
    
    # Document reference (if saved to Drive)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="company_packs")
    job = relationship("Job", backref="company_packs")
    document = relationship("Document", backref="company_packs")
    
    __table_args__ = (
        Index('idx_user_job', 'user_id', 'job_id'),
    )
    
    def __repr__(self):
        return f"<CompanyPack(id={self.id}, user_id={self.user_id}, job_id={self.job_id})>"
