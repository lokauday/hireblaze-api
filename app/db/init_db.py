from app.db.session import engine
from app.db.base import Base
# Import all models to ensure they register with Base.metadata
from app.db.models.user import User
from app.db.models.resume import Resume
from app.db.models.job import JobDescription
from app.db.models.application import Application
from app.db.models.ats_score import ATSScore
from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
from app.db.models.candidate_benchmark import CandidateBenchmark
from app.db.models.interview_evaluation import InterviewEvaluation
from app.db.models.interview_session import InterviewSession


Base.metadata.create_all(bind=engine)
