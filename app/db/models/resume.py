from sqlalchemy import Column, Integer, String, ForeignKey, Text
from app.db.base import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    original_file = Column(String)
    parsed_text = Column(Text)
