"""fix_duplicate_index_names

Revision ID: aefa9a8b4271
Revises: 2f8204397ff4
Create Date: 2026-01-10 13:47:19.860821

Fixes duplicate index names across different tables by renaming them to be unique.
This migration safely handles existing indexes in production databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aefa9a8b4271'
down_revision: Union[str, None] = '2f8204397ff4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename duplicate indexes to be unique per table.
    
    The old indexes (idx_user_created, idx_job_created, etc.) were used across
    multiple tables, causing conflicts in PostgreSQL where index names must be unique.
    This migration safely drops old indexes and creates new uniquely-named ones.
    
    All operations use IF EXISTS/IF NOT EXISTS to be idempotent.
    """
    from sqlalchemy import text
    import logging
    
    logger = logging.getLogger(__name__)
    bind = op.get_bind()
    
    # Helper function to check if index exists
    def index_exists(index_name: str, table_name: str) -> bool:
        try:
            result = bind.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND tablename = :table_name 
                    AND indexname = :index_name
                )
            """), {"table_name": table_name, "index_name": index_name})
            return result.scalar()
        except Exception:
            return False
    
    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        try:
            result = bind.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name 
                    AND column_name = :column_name
                )
            """), {"table_name": table_name, "column_name": column_name})
            return result.scalar()
        except Exception:
            return False
    
    # Fix interview_packs indexes: drop old, create new
    op.execute(text('DROP INDEX IF EXISTS "idx_user_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_job_created"'))
    if not index_exists('idx_interview_pack_user_created', 'interview_packs'):
        op.execute(text('CREATE INDEX "idx_interview_pack_user_created" ON "interview_packs" ("user_id", "created_at")'))
    if not index_exists('idx_interview_pack_job_created', 'interview_packs'):
        op.execute(text('CREATE INDEX "idx_interview_pack_job_created" ON "interview_packs" ("job_id", "created_at")'))
    
    # Fix job_postings indexes: drop old, create new
    op.execute(text('DROP INDEX IF EXISTS "idx_user_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_company_title"'))
    if not index_exists('idx_job_posting_user_created', 'job_postings'):
        op.execute(text('CREATE INDEX "idx_job_posting_user_created" ON "job_postings" ("user_id", "created_at")'))
    if not index_exists('idx_job_posting_company_title', 'job_postings'):
        op.execute(text('CREATE INDEX "idx_job_posting_company_title" ON "job_postings" ("company", "title")'))
    
    # Fix resumes indexes: drop old, create new
    op.execute(text('DROP INDEX IF EXISTS "idx_user_created"'))
    if not index_exists('idx_resume_user_created', 'resumes'):
        # Check if created_at column exists before creating index
        if column_exists('resumes', 'created_at'):
            op.execute(text('CREATE INDEX "idx_resume_user_created" ON "resumes" ("user_id", "created_at")'))
        else:
            logger.warning('Skipping idx_resume_user_created: column resumes.created_at does not exist')
    
    # Fix outreach_messages indexes (if table exists)
    try:
        op.execute(text('DROP INDEX IF EXISTS "idx_job_created"'))
        op.execute(text('DROP INDEX IF EXISTS "idx_user_type"'))
        if not index_exists('idx_outreach_message_job_created', 'outreach_messages'):
            op.execute(text('CREATE INDEX "idx_outreach_message_job_created" ON "outreach_messages" ("job_id", "created_at")'))
        if not index_exists('idx_outreach_message_user_type', 'outreach_messages'):
            op.execute(text('CREATE INDEX "idx_outreach_message_user_type" ON "outreach_messages" ("user_id", "type")'))
    except Exception:
        pass  # Table might not exist


def downgrade() -> None:
    """
    Revert index names back to original (not recommended due to conflicts).
    This downgrade uses IF EXISTS to be idempotent.
    """
    from sqlalchemy import text
    
    # Drop new indexes using IF EXISTS
    op.execute(text('DROP INDEX IF EXISTS "idx_interview_pack_user_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_interview_pack_job_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_job_posting_user_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_job_posting_company_title"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_resume_user_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_outreach_message_job_created"'))
    op.execute(text('DROP INDEX IF EXISTS "idx_outreach_message_user_type"'))
    
    # Note: We cannot recreate the old duplicate-named indexes as they would conflict
    # This downgrade is intentionally incomplete to prevent database corruption
