"""
Database models module.

This module imports all database models to ensure they are registered with SQLAlchemy's Base.metadata
before table creation.

All models must be imported here to be included in database migrations and table creation.
"""
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
from app.db.models.ai_usage import AIUsage
from app.db.models.resume import Resume
from app.db.models.job import Job, JobDescription
from app.db.models.job_posting import JobPosting
from app.db.models.match_analysis import MatchAnalysis
from app.db.models.interview_pack import InterviewPack
from app.db.models.outreach_message import OutreachMessage, OutreachType
from app.db.models.document import Document
from app.db.models.application import Application
from app.db.models.ats_score import ATSScore
from app.db.models.candidate_benchmark import CandidateBenchmark
from app.db.models.interview_evaluation import InterviewEvaluation
from app.db.models.interview_session import InterviewSession

# Explicitly export all models for clarity
__all__ = [
    "User",
    "Subscription",
    "UsageEvent",
    "AIUsage",
    "Resume",
    "Job",
    "JobDescription",
    "JobPosting",
    "MatchAnalysis",
    "InterviewPack",
    "OutreachMessage",
    "OutreachType",
    "Document",
    "Application",
    "ATSScore",
    "CandidateBenchmark",
    "InterviewEvaluation",
    "InterviewSession",
]
