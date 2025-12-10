from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.base import Base

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company = Column(String)
    role = Column(String)
    jd_text = Column(Text)
