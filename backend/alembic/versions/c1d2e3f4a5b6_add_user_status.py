"""add user status column and expand role enum

Revision ID: c1d2e3f4a5b6
Revises: b3c4d5e6f7a8
Create Date: 2026-08-04 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c1d2e3f4a5b6'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {c['name'] for c in inspector.get_columns('user')}

    if 'status' not in columns:
        op.add_column(
            'user',
            sa.Column(
                'status',
                sa.Enum('active', 'disabled', 'pending', name='user_status'),
                nullable=False,
                server_default='active',
            ),
        )
        # 把 is_active 的数据同步到 status
        connection.execute(
            sa.text("UPDATE user SET status = 'disabled' WHERE is_active = 0")
        )

    # 扩展 role 枚举，增加 hr 角色（SQLite 下用 batch_alter_table）
    existing_enum = sa.Enum('admin', 'candidate', name='user_role')
    # 直接使用字符串列名方式，避免 enum 重命名问题
    if connection.dialect.name == 'sqlite':
        with op.batch_alter_table('user') as batch_op:
            batch_op.alter_column(
                'role',
                type_=sa.Enum('admin', 'candidate', 'hr', name='user_role'),
                existing_type=existing_enum,
                nullable=False,
            )
    else:
        # MySQL 下使用 ALTER 直接重定义枚举
        op.execute(
            "ALTER TABLE user MODIFY role ENUM('admin','candidate','hr') NOT NULL DEFAULT 'candidate'"
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == 'sqlite':
        with op.batch_alter_table('user') as batch_op:
            batch_op.alter_column(
                'role',
                type_=sa.Enum('admin', 'candidate', name='user_role'),
                nullable=False,
            )
    else:
        op.execute(
            "ALTER TABLE user MODIFY role ENUM('admin','candidate') NOT NULL DEFAULT 'candidate'"
        )

    inspector = sa.inspect(connection)
    columns = {c['name'] for c in inspector.get_columns('user')}
    if 'status' in columns:
        op.drop_column('status')
