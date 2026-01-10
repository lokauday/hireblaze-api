"""
Database initialization module.

Creates all database tables on startup.
This runs once when the FastAPI application starts (not per request).

IMPORTANT: All models MUST be imported here before create_all() is called,
otherwise their tables will not be created.
"""
import logging
from app.db.session import engine
from app.db.base import Base

# Import ALL models to ensure they register with Base.metadata
# This MUST happen before create_all() is called
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
from app.db.models.resume import Resume
from app.db.models.job import Job, JobDescription
from app.db.models.job_posting import JobPosting
from app.db.models.match_analysis import MatchAnalysis
from app.db.models.interview_pack import InterviewPack
from app.db.models.outreach_message import OutreachMessage
from app.db.models.document import Document
from app.db.models.application import Application
from app.db.models.ats_score import ATSScore
from app.db.models.candidate_benchmark import CandidateBenchmark
from app.db.models.interview_evaluation import InterviewEvaluation
from app.db.models.interview_session import InterviewSession

logger = logging.getLogger(__name__)


def init_db():
    """
    Initialize database tables on startup.
    
    This function:
    1. Imports all models (they register with Base.metadata)
    2. Calls Base.metadata.create_all() to create tables if they don't exist
    
    Works for both PostgreSQL (production) and SQLite (local development).
    SQLAlchemy's create_all() is idempotent - it only creates missing tables.
    
    Handles duplicate index/table errors gracefully for cases where database
    already has some schema objects (e.g., from migrations).
    
    This should be called once at application startup via FastAPI's startup event.
    """
    try:
        # All models are imported above, so Base.metadata contains all table definitions
        # create_all() creates tables that don't exist (idempotent)
        # In PostgreSQL, if indexes already exist, we catch and ignore those errors
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
    except Exception as e:
        error_msg = str(e).lower()
        # In PostgreSQL, if objects already exist, we can safely ignore these errors
        # as they indicate the database is already initialized (likely from migrations)
        if any(keyword in error_msg for keyword in ['already exists', 'duplicate', 'relation']):
            logger.warning(f"Some database objects already exist (likely from migrations): {e}")
            logger.info("Continuing startup - database appears to be initialized")
        else:
            # For other errors (connection issues, permission problems, etc.), we should fail
            logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
            raise
