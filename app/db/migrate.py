"""
Database migration runner for Alembic migrations.
"""
import logging
import os
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

ADVISORY_LOCK_ID = 987654321


def run_migrations():
    """
    Run Alembic migrations to head revision.
    Uses advisory locks to prevent concurrent migrations.
    """
    from app.core import config as app_config
    
    if not app_config.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    
    logger.info("RUN_MIGRATIONS=1 -> running alembic upgrade head")
    
    # Create Alembic config
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)
    alembic_cfg.set_main_option("version_table_schema", "public")
    
    # Create engine for lock management
    engine = create_engine(app_config.DATABASE_URL, pool_pre_ping=True)
    lock_conn = None
    
    try:
        if app_config.DATABASE_URL.startswith("postgresql"):
            # Acquire advisory lock (keep connection open to hold lock)
            lock_conn = engine.connect()
            try:
                lock_conn.execute(text(f"SELECT pg_advisory_lock({ADVISORY_LOCK_ID})"))
                lock_conn.commit()
                logger.info("Migration lock acquired")
            except Exception as lock_error:
                logger.warning(f"Could not acquire advisory lock: {lock_error}")
                if lock_conn:
                    lock_conn.close()
                    lock_conn = None
        
        # Run migrations (idempotent - Alembic handles state)
        command.upgrade(alembic_cfg, "head")
        
        # Explicitly stamp to head to ensure version table is set
        try:
            command.stamp(alembic_cfg, "head")
        except Exception:
            pass  # Already at head, ignore
        
        logger.info("Migrations complete")
        
    except Exception as e:
        logger.exception("Migration failed")
        raise
    finally:
        # Release advisory lock
        if lock_conn:
            try:
                if app_config.DATABASE_URL.startswith("postgresql"):
                    lock_conn.execute(text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_ID})"))
                    lock_conn.commit()
                lock_conn.close()
            except Exception:
                pass
        engine.dispose()
