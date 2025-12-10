from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    status = Column(String, default="active")  # active / ended
    created_at = Column(DateTime(timezone=True), server_default=func.now())
