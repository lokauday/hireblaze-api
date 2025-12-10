from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Float
from sqlalchemy.sql import func
from app.db.base import Base

class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    
    communication_score = Column(Float)
    technical_score = Column(Float)
    confidence_score = Column(Float)
    role_fit_score = Column(Float)

    strengths = Column(Text)
    weaknesses = Column(Text)
    improvement_plan = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
