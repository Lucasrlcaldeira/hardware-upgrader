"""games and game_benchmarks tables

Revision ID: bd316ac54011
Revises: c7e91c23d9e2
Create Date: 2026-09-01 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bd316ac54011'
down_revision: str | Sequence[str] | None = 'c7e91c23d9e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('games',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_games_title'), 'games', ['title'], unique=True)
    op.create_table('game_benchmarks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game_id', sa.Integer(), nullable=False),
    sa.Column('gpu_id', sa.Integer(), nullable=False),
    sa.Column('resolution', sa.String(length=10), nullable=False),
    sa.Column('avg_fps', sa.Integer(), nullable=False),
    sa.Column('test_cpu_model', sa.String(length=100), nullable=False),
    sa.Column('quality_preset_note', sa.Text(), nullable=False),
    sa.Column('source_name', sa.String(length=100), nullable=False),
    sa.Column('source_url', sa.String(length=300), nullable=False),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.ForeignKeyConstraint(['gpu_id'], ['gpu_models.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_benchmarks_game_id'), 'game_benchmarks', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_benchmarks_gpu_id'), 'game_benchmarks', ['gpu_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_game_benchmarks_gpu_id'), table_name='game_benchmarks')
    op.drop_index(op.f('ix_game_benchmarks_game_id'), table_name='game_benchmarks')
    op.drop_table('game_benchmarks')
    op.drop_index(op.f('ix_games_title'), table_name='games')
    op.drop_table('games')
