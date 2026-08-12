"""add_knowledge_base_models

Revision ID: 3a551392374b
Revises: 35e71f8a93d8
Create Date: 2026-08-06 11:21:16.236949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3a551392374b'
down_revision: Union[str, None] = '35e71f8a93d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create position table
    op.create_table(
        'position',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_position_name'), 'position', ['name'], unique=True)

    # Create scoring_template table
    op.create_table(
        'scoring_template',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['position.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scoring_template_position_id'), 'scoring_template', ['position_id'], unique=False)

    # Create scoring_rule table
    op.create_table(
        'scoring_rule',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=200), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('key_points', sa.Text(), nullable=True),
        sa.Column('deduction_rules', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['scoring_template.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scoring_rule_template_id'), 'scoring_rule', ['template_id'], unique=False)

    # Add scoring template reference to ai_score_record
    op.add_column('ai_score_record', sa.Column('scoring_template_id', sa.Integer(), nullable=True))
    op.add_column('ai_score_record', sa.Column('scoring_rule_versions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_score_record', 'scoring_rule_versions')
    op.drop_column('ai_score_record', 'scoring_template_id')
    op.drop_index(op.f('ix_scoring_rule_template_id'), table_name='scoring_rule')
    op.drop_table('scoring_rule')
    op.drop_index(op.f('ix_scoring_template_position_id'), table_name='scoring_template')
    op.drop_table('scoring_template')
    op.drop_index(op.f('ix_position_name'), table_name='position')
    op.drop_table('position')
