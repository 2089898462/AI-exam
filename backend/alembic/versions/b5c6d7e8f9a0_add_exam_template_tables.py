"""S4.2 固定试卷模板体系

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f7
Create Date: 2026-08-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5c6d7e8f9a0'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 exam_template 表
    op.create_table(
        'exam_template',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', name='template_status'), nullable=False, server_default='active'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_template_id'), 'exam_template', ['id'], unique=False)

    # 创建 template_question 表
    op.create_table(
        'template_question',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('question_no', sa.String(length=20), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('type', sa.Enum('single_choice', 'multiple_choice', 'true_false', 'short_answer', name='template_question_type'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['exam_template.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_template_question_template_id'), 'template_question', ['template_id'], unique=False)

    # 为 answer_record 添加 question_snapshot 字段
    op.add_column('answer_record', sa.Column('question_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    # 删除 answer_record 的 question_snapshot 字段
    op.drop_column('answer_record', 'question_snapshot')

    # 删除 template_question 表
    op.drop_index(op.f('ix_template_question_template_id'), table_name='template_question')
    op.drop_table('template_question')

    # 删除 exam_template 表
    op.drop_index(op.f('ix_exam_template_id'), table_name='exam_template')
    op.drop_table('exam_template')
