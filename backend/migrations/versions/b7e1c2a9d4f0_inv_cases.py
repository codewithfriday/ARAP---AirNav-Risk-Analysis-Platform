"""investigation expert system case library (v0.7)

Revision ID: b7e1c2a9d4f0
Revises: 70368d3b4414
Create Date: 2026-09-29 15:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7e1c2a9d4f0'
down_revision: Union[str, Sequence[str], None] = '70368d3b4414'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('inv_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ref', sa.String(length=30), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('occurred', sa.String(length=20), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('report_text', sa.Text(), nullable=False),
    sa.Column('model', JSON, nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('provenance', JSON, nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('approved_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inv_cases_ref'), 'inv_cases', ['ref'], unique=True)
    op.create_index(op.f('ix_inv_cases_category'), 'inv_cases', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inv_cases_category'), table_name='inv_cases')
    op.drop_index(op.f('ix_inv_cases_ref'), table_name='inv_cases')
    op.drop_table('inv_cases')
