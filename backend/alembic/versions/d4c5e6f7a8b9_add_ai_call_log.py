"""S4.4-C1 新增 ai_call_log 表

Revision ID: d4c5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-08-06

变更说明：
- 新增 ai_call_log 表：AI 调用审计日志表
- 用于记录 AI Agent 调用行为，支持链路追踪
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4c5e6f7a8b9'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_call_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('caller_user_id', sa.Integer(), nullable=False),
        sa.Column('caller_role', sa.String(length=20), nullable=False, server_default='admin'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='ai_agent'),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False, server_default='GET'),
        sa.Column('request_summary', sa.Text(), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('called_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 索引
    op.create_index(op.f('ix_ai_call_log_trace_id'), 'ai_call_log', ['trace_id'])
    op.create_index(op.f('ix_ai_call_log_request_id'), 'ai_call_log', ['request_id'])
    op.create_index(op.f('ix_ai_call_log_caller_user_id'), 'ai_call_log', ['caller_user_id'])
    op.create_index(op.f('ix_ai_call_log_status'), 'ai_call_log', ['status'])
    op.create_index(op.f('ix_ai_call_log_called_at'), 'ai_call_log', ['called_at'])
    op.create_index(op.f('ix_ai_call_log_endpoint'), 'ai_call_log', ['endpoint'])
    op.create_index('ix_ai_call_log_trace_id_called_at', 'ai_call_log', ['trace_id', 'called_at'])
    op.create_index('ix_ai_call_log_caller_status', 'ai_call_log', ['caller_user_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_ai_call_log_caller_status', table_name='ai_call_log')
    op.drop_index('ix_ai_call_log_trace_id_called_at', table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_endpoint'), table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_called_at'), table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_status'), table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_caller_user_id'), table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_request_id'), table_name='ai_call_log')
    op.drop_index(op.f('ix_ai_call_log_trace_id'), table_name='ai_call_log')
    op.drop_table('ai_call_log')