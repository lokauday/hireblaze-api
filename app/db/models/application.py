from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.base import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company = Column(String)
    role = Column(String)
    status = Column(String, default="Applied")
    visa_compatible = Column(Boolean, default=True)
