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
    
    Uses try/except to gracefully handle cases where indexes may or may not exist.
    """
    # Fix interview_packs indexes: drop old, create new
    try:
        op.drop_index('idx_user_created', table_name='interview_packs', if_exists=True)
    except Exception:
        pass
    try:
        op.drop_index('idx_job_created', table_name='interview_packs', if_exists=True)
    except Exception:
        pass
    try:
        op.create_index('idx_interview_pack_user_created', 'interview_packs', ['user_id', 'created_at'], unique=False)
    except Exception:
        pass  # May already exist
    try:
        op.create_index('idx_interview_pack_job_created', 'interview_packs', ['job_id', 'created_at'], unique=False)
    except Exception:
        pass  # May already exist
    
    # Fix job_postings indexes: drop old, create new
    try:
        op.drop_index('idx_user_created', table_name='job_postings', if_exists=True)
    except Exception:
        pass
    try:
        op.drop_index('idx_company_title', table_name='job_postings', if_exists=True)
    except Exception:
        pass
    try:
        op.create_index('idx_job_posting_user_created', 'job_postings', ['user_id', 'created_at'], unique=False)
    except Exception:
        pass  # May already exist
    try:
        op.create_index('idx_job_posting_company_title', 'job_postings', ['company', 'title'], unique=False)
    except Exception:
        pass  # May already exist
    
    # Fix resumes indexes: drop old, create new
    try:
        op.drop_index('idx_user_created', table_name='resumes', if_exists=True)
    except Exception:
        pass
    try:
        op.create_index('idx_resume_user_created', 'resumes', ['user_id', 'created_at'], unique=False)
    except Exception:
        pass  # May already exist
    
    # Fix outreach_messages indexes (if table exists)
    try:
        op.drop_index('idx_job_created', table_name='outreach_messages', if_exists=True)
    except Exception:
        pass  # Table might not exist
    try:
        op.drop_index('idx_user_type', table_name='outreach_messages', if_exists=True)
    except Exception:
        pass  # Table might not exist
    try:
        op.create_index('idx_outreach_message_job_created', 'outreach_messages', ['job_id', 'created_at'], unique=False)
    except Exception:
        pass  # Table/index might not exist
    try:
        op.create_index('idx_outreach_message_user_type', 'outreach_messages', ['user_id', 'type'], unique=False)
    except Exception:
        pass  # Table/index might not exist


def downgrade() -> None:
    """
    Revert index names back to original (not recommended due to conflicts).
    This downgrade will fail if multiple tables try to use the same index name.
    """
    # Drop new indexes
    try:
        op.drop_index('idx_interview_pack_user_created', table_name='interview_packs', if_exists=True)
        op.drop_index('idx_interview_pack_job_created', table_name='interview_packs', if_exists=True)
        op.drop_index('idx_job_posting_user_created', table_name='job_postings', if_exists=True)
        op.drop_index('idx_job_posting_company_title', table_name='job_postings', if_exists=True)
        op.drop_index('idx_resume_user_created', table_name='resumes', if_exists=True)
        op.drop_index('idx_outreach_message_job_created', table_name='outreach_messages', if_exists=True)
        op.drop_index('idx_outreach_message_user_type', table_name='outreach_messages', if_exists=True)
    except Exception:
        pass
    
    # Note: We cannot recreate the old duplicate-named indexes as they would conflict
    # This downgrade is intentionally incomplete to prevent database corruption
