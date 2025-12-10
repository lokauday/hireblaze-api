from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class CandidateBenchmark(Base):
    __tablename__ = "candidate_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)

    candidate_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))

    communication_score = Column(Float)
    technical_score = Column(Float)
    confidence_score = Column(Float)
    role_fit_score = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
