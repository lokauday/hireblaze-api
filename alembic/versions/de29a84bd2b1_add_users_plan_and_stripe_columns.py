"""add_users_plan_and_stripe_columns

Revision ID: de29a84bd2b1
Revises: aefa9a8b4271
Create Date: 2026-01-12 20:12:40.351563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de29a84bd2b1'
down_revision: Union[str, None] = 'aefa9a8b4271'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add plan and Stripe subscription columns to users table."""
    from sqlalchemy import inspect
    
    # Check if columns already exist (idempotent migration)
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add plan column if it doesn't exist
    if 'plan' not in columns:
        op.add_column('users', sa.Column('plan', sa.String(), nullable=False, server_default='free'))
    
    # Add stripe_customer_id column if it doesn't exist
    if 'stripe_customer_id' not in columns:
        op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))
        op.create_index(op.f('ix_users_stripe_customer_id'), 'users', ['stripe_customer_id'], unique=False)
    
    # Add stripe_subscription_id column if it doesn't exist
    if 'stripe_subscription_id' not in columns:
        op.add_column('users', sa.Column('stripe_subscription_id', sa.String(), nullable=True))
    
    # Add stripe_price_id column if it doesn't exist
    if 'stripe_price_id' not in columns:
        op.add_column('users', sa.Column('stripe_price_id', sa.String(), nullable=True))
    
    # Add plan_status column if it doesn't exist
    if 'plan_status' not in columns:
        op.add_column('users', sa.Column('plan_status', sa.String(), nullable=True))
    
    # Add current_period_end column if it doesn't exist
    if 'current_period_end' not in columns:
        op.add_column('users', sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove plan and Stripe subscription columns from users table."""
    # Drop columns in reverse order
    op.drop_column('users', 'current_period_end')
    op.drop_column('users', 'plan_status')
    op.drop_column('users', 'stripe_price_id')
    op.drop_column('users', 'stripe_subscription_id')
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')
    op.drop_column('users', 'stripe_customer_id')
    op.drop_column('users', 'plan')
