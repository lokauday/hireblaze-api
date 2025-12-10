from app.db.session import engine
from app.db.base import Base
from app.db.models.user import User
from app.db.models.resume import Resume
from app.db.models.job import JobDescription
from app.db.models.application import Application
from app.db.models.ats_score import ATSScore


Base.metadata.create_all(bind=engine)
