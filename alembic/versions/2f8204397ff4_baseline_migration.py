"""baseline_migration

Revision ID: 2f8204397ff4
Revises: 
Create Date: 2026-01-09 19:33:03.295395

Production-safe migration: Only creates new tables, does not modify existing ones.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '2f8204397ff4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """
    Production-safe upgrade: Only creates new tables if they don't exist.
    Does not modify existing tables to avoid breaking production deployments.
    """
    # Create job_postings table
    if not table_exists('job_postings'):
        op.create_table('job_postings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('source_url', sa.String(), nullable=True),
            sa.Column('company', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('location', sa.String(), nullable=True),
            sa.Column('jd_text', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_company_title', 'job_postings', ['company', 'title'], unique=False)
        op.create_index('idx_user_created', 'job_postings', ['user_id', 'created_at'], unique=False)
        op.create_index(op.f('ix_job_postings_company'), 'job_postings', ['company'], unique=False)
        op.create_index(op.f('ix_job_postings_created_at'), 'job_postings', ['created_at'], unique=False)
        op.create_index(op.f('ix_job_postings_id'), 'job_postings', ['id'], unique=False)
        op.create_index(op.f('ix_job_postings_title'), 'job_postings', ['title'], unique=False)
        op.create_index(op.f('ix_job_postings_user_id'), 'job_postings', ['user_id'], unique=False)
    
    # Create interview_packs table
    if not table_exists('interview_packs'):
        op.create_table('interview_packs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('content', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_job_created', 'interview_packs', ['job_id', 'created_at'], unique=False)
        op.create_index('idx_user_created', 'interview_packs', ['user_id', 'created_at'], unique=False)
        op.create_index(op.f('ix_interview_packs_created_at'), 'interview_packs', ['created_at'], unique=False)
        op.create_index(op.f('ix_interview_packs_id'), 'interview_packs', ['id'], unique=False)
        op.create_index(op.f('ix_interview_packs_job_id'), 'interview_packs', ['job_id'], unique=False)
        op.create_index(op.f('ix_interview_packs_user_id'), 'interview_packs', ['user_id'], unique=False)
    
    # Create match_analyses table
    if not table_exists('match_analyses'):
        op.create_table('match_analyses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('resume_id', sa.Integer(), nullable=True),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('score', sa.Float(), nullable=False),
            sa.Column('overlap', sa.JSON(), nullable=True),
            sa.Column('missing', sa.JSON(), nullable=True),
            sa.Column('risks', sa.JSON(), nullable=True),
            sa.Column('improvement_plan', sa.JSON(), nullable=True),
            sa.Column('recruiter_lens', sa.JSON(), nullable=True),
            sa.Column('narrative', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ),
            sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_resume_job', 'match_analyses', ['resume_id', 'job_id'], unique=False)
        op.create_index('idx_user_score', 'match_analyses', ['user_id', 'score'], unique=False)
        op.create_index(op.f('ix_match_analyses_created_at'), 'match_analyses', ['created_at'], unique=False)
        op.create_index(op.f('ix_match_analyses_id'), 'match_analyses', ['id'], unique=False)
        op.create_index(op.f('ix_match_analyses_job_id'), 'match_analyses', ['job_id'], unique=False)
        op.create_index(op.f('ix_match_analyses_resume_id'), 'match_analyses', ['resume_id'], unique=False)
        op.create_index(op.f('ix_match_analyses_score'), 'match_analyses', ['score'], unique=False)
        op.create_index(op.f('ix_match_analyses_user_id'), 'match_analyses', ['user_id'], unique=False)
    
    # Create outreach_messages table (need to create enum type first for PostgreSQL)
    if not table_exists('outreach_messages'):
        # Create enum type if it doesn't exist (PostgreSQL specific)
        bind = op.get_bind()
        if bind.dialect.name == 'postgresql':
            op.execute("DO $$ BEGIN CREATE TYPE outreachtype AS ENUM ('RECRUITER_FOLLOWUP', 'LINKEDIN_DM', 'THANK_YOU', 'REFERRAL_ASK'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
        
        op.create_table('outreach_messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('type', sa.Enum('RECRUITER_FOLLOWUP', 'LINKEDIN_DM', 'THANK_YOU', 'REFERRAL_ASK', name='outreachtype'), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_job_created', 'outreach_messages', ['job_id', 'created_at'], unique=False)
        op.create_index('idx_user_type', 'outreach_messages', ['user_id', 'type'], unique=False)
        op.create_index(op.f('ix_outreach_messages_created_at'), 'outreach_messages', ['created_at'], unique=False)
        op.create_index(op.f('ix_outreach_messages_id'), 'outreach_messages', ['id'], unique=False)
        op.create_index(op.f('ix_outreach_messages_job_id'), 'outreach_messages', ['job_id'], unique=False)
        op.create_index(op.f('ix_outreach_messages_type'), 'outreach_messages', ['type'], unique=False)
        op.create_index(op.f('ix_outreach_messages_user_id'), 'outreach_messages', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade: Drop new tables only."""
    op.drop_index(op.f('ix_outreach_messages_user_id'), table_name='outreach_messages')
    op.drop_index(op.f('ix_outreach_messages_type'), table_name='outreach_messages')
    op.drop_index(op.f('ix_outreach_messages_job_id'), table_name='outreach_messages')
    op.drop_index(op.f('ix_outreach_messages_id'), table_name='outreach_messages')
    op.drop_index(op.f('ix_outreach_messages_created_at'), table_name='outreach_messages')
    op.drop_index('idx_user_type', table_name='outreach_messages')
    op.drop_index('idx_job_created', table_name='outreach_messages')
    op.drop_table('outreach_messages')
    
    op.drop_index(op.f('ix_match_analyses_user_id'), table_name='match_analyses')
    op.drop_index(op.f('ix_match_analyses_score'), table_name='match_analyses')
    op.drop_index(op.f('ix_match_analyses_resume_id'), table_name='match_analyses')
    op.drop_index(op.f('ix_match_analyses_job_id'), table_name='match_analyses')
    op.drop_index(op.f('ix_match_analyses_id'), table_name='match_analyses')
    op.drop_index(op.f('ix_match_analyses_created_at'), table_name='match_analyses')
    op.drop_index('idx_user_score', table_name='match_analyses')
    op.drop_index('idx_resume_job', table_name='match_analyses')
    op.drop_table('match_analyses')
    
    op.drop_index(op.f('ix_interview_packs_user_id'), table_name='interview_packs')
    op.drop_index(op.f('ix_interview_packs_job_id'), table_name='interview_packs')
    op.drop_index(op.f('ix_interview_packs_id'), table_name='interview_packs')
    op.drop_index(op.f('ix_interview_packs_created_at'), table_name='interview_packs')
    op.drop_index('idx_user_created', table_name='interview_packs')
    op.drop_index('idx_job_created', table_name='interview_packs')
    op.drop_table('interview_packs')
    
    op.drop_index(op.f('ix_job_postings_user_id'), table_name='job_postings')
    op.drop_index(op.f('ix_job_postings_title'), table_name='job_postings')
    op.drop_index(op.f('ix_job_postings_id'), table_name='job_postings')
    op.drop_index(op.f('ix_job_postings_created_at'), table_name='job_postings')
    op.drop_index(op.f('ix_job_postings_company'), table_name='job_postings')
    op.drop_index('idx_user_created', table_name='job_postings')
    op.drop_index('idx_company_title', table_name='job_postings')
    op.drop_table('job_postings')
