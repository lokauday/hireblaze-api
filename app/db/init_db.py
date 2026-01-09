"""
Database initialization module.

Creates all database tables on startup if using PostgreSQL (production).
SQLite tables are created automatically, so we skip create_all for local development.
"""
import logging
from app.db.session import engine
from app.db.base import Base
from app.core.config import DATABASE_URL

# Import all models to ensure they register with Base.metadata
# This MUST happen before create_all() is called
from app.db.models import (
    User,
    Subscription,
    UsageEvent,
    Resume,
    JobDescription,
    Application,
    ATSScore,
    CandidateBenchmark,
    InterviewEvaluation,
    InterviewSession,
)

logger = logging.getLogger(__name__)


def init_db():
    """
    Initialize database tables on startup.
    
    Only creates tables if DATABASE_URL is set and points to PostgreSQL (production).
    For SQLite (local development), tables are created automatically, so we skip this.
    
    This should be called once at application startup, not on every request.
    """
    # Check if DATABASE_URL is set and points to PostgreSQL
    if not DATABASE_URL:
        logger.info("DATABASE_URL not set. Skipping table creation (using default SQLite).")
        return
    
    # Check if this is a PostgreSQL connection
    is_postgres = (
        DATABASE_URL.startswith("postgresql://") or
        DATABASE_URL.startswith("postgres://") or
        "postgresql+psycopg2://" in DATABASE_URL or
        "postgresql+psycopg2" in DATABASE_URL
    )
    
    if not is_postgres:
        logger.info(f"DATABASE_URL points to non-Postgres database: {DATABASE_URL.split('://')[0] if '://' in DATABASE_URL else DATABASE_URL}. Skipping table creation (tables created automatically).")
        return
    
    try:
        logger.info("Creating DB tables if missing...")
        
        # All models are already imported via app.db.models
        # This ensures Base.metadata contains all table definitions
        Base.metadata.create_all(bind=engine)
        
        logger.info("DB tables ensured.")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        # Don't raise - allow app to start even if table creation fails
        # This prevents startup crashes in case of DB connection issues
        logger.warning("Application will continue, but database operations may fail.")
