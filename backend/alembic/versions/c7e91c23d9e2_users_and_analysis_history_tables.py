"""users and analysis history tables

Revision ID: c7e91c23d9e2
Revises: 0e9f02dc2695
Create Date: 2026-09-01 04:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7e91c23d9e2'
down_revision: str | Sequence[str] | None = '0e9f02dc2695'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('analysis_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('profile', sa.String(length=30), nullable=False),
    sa.Column('report', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_history_created_at'), 'analysis_history', ['created_at'], unique=False)
    op.create_index(op.f('ix_analysis_history_profile'), 'analysis_history', ['profile'], unique=False)
    op.create_index(op.f('ix_analysis_history_user_id'), 'analysis_history', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analysis_history_user_id'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_profile'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_created_at'), table_name='analysis_history')
    op.drop_table('analysis_history')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
