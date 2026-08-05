"""S3.1.1 restructure exam_record and answer_record for candidate flow

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6g7h8i9
Create Date: 2026-08-04 23:59:00.000000

变更说明：
- exam_record: 移除 user_id 外键，新增候选人嵌入式身份字段，重命名 total_score→score，扩展状态枚举
- answer_record: 重命名 answer→answer_content，移除 score_type，重命名 score_detail→ai_comment，新增 is_correct
"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # ============================================================
    # exam_record 表重建
    # ============================================================
    op.execute("""
        CREATE TABLE exam_record_new (
            id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            candidate_name VARCHAR(64) NOT NULL DEFAULT '',
            candidate_phone VARCHAR(20),
            candidate_email VARCHAR(128),
            status VARCHAR(16) NOT NULL DEFAULT 'not_started',
            started_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            submitted_at DATETIME,
            score NUMERIC(8, 2),
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(exam_id) REFERENCES exam (id)
        )
    """)

    # 迁移数据
    op.execute("""
        INSERT INTO exam_record_new (id, exam_id, candidate_name, candidate_phone, candidate_email,
                                     status, started_at, submitted_at, score, created_at, updated_at)
        SELECT id, exam_id, 'Unknown', NULL, NULL,
               status, started_at, submitted_at, total_score, created_at, updated_at
        FROM exam_record
    """)

    # 替换旧表
    op.execute("DROP TABLE exam_record")
    op.execute("ALTER TABLE exam_record_new RENAME TO exam_record")

    # 创建索引
    op.execute("CREATE INDEX ix_exam_record_exam_id ON exam_record (exam_id)")

    # ============================================================
    # answer_record 表重建
    # ============================================================
    op.execute("""
        CREATE TABLE answer_record_new (
            id INTEGER NOT NULL,
            exam_record_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_content TEXT,
            score NUMERIC(5, 2),
            is_correct BOOLEAN,
            ai_comment TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(exam_record_id) REFERENCES exam_record (id),
            FOREIGN KEY(question_id) REFERENCES question (id),
            CONSTRAINT uq_answer_record_question UNIQUE (exam_record_id, question_id)
        )
    """)

    # 迁移数据（score_detail JSON → ai_comment TEXT，仅保留文本）
    op.execute("""
        INSERT INTO answer_record_new (id, exam_record_id, question_id, answer_content,
                                       score, is_correct, ai_comment, created_at, updated_at)
        SELECT id, exam_record_id, question_id, answer,
               score, NULL, score_detail, created_at, updated_at
        FROM answer_record
    """)

    # 替换旧表
    op.execute("DROP TABLE answer_record")
    op.execute("ALTER TABLE answer_record_new RENAME TO answer_record")

    # 创建索引
    op.execute("CREATE INDEX ix_answer_record_exam_record_id ON answer_record (exam_record_id)")
    op.execute("CREATE INDEX ix_answer_record_question_id ON answer_record (question_id)")


def downgrade() -> None:
    # ============================================================
    # answer_record 表回滚
    # ============================================================
    op.execute("""
        CREATE TABLE answer_record_old (
            id INTEGER NOT NULL,
            exam_record_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT,
            score NUMERIC(5, 2),
            score_type VARCHAR(4),
            score_detail JSON,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(exam_record_id) REFERENCES exam_record (id),
            FOREIGN KEY(question_id) REFERENCES question (id),
            CONSTRAINT uq_answer_record_question UNIQUE (exam_record_id, question_id)
        )
    """)

    op.execute("""
        INSERT INTO answer_record_old (id, exam_record_id, question_id, answer, score,
                                       score_type, score_detail, created_at, updated_at)
        SELECT id, exam_record_id, question_id, answer_content, score,
               NULL, ai_comment, created_at, updated_at
        FROM answer_record
    """)

    op.execute("DROP TABLE answer_record")
    op.execute("ALTER TABLE answer_record_old RENAME TO answer_record")
    op.execute("CREATE INDEX ix_answer_record_exam_record_id ON answer_record (exam_record_id)")
    op.execute("CREATE INDEX ix_answer_record_question_id ON answer_record (question_id)")

    # ============================================================
    # exam_record 表回滚
    # ============================================================
    op.execute("""
        CREATE TABLE exam_record_old (
            id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status VARCHAR(11) NOT NULL,
            started_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            submitted_at DATETIME,
            total_score NUMERIC(8, 2),
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(exam_id) REFERENCES exam (id),
            FOREIGN KEY(user_id) REFERENCES user (id)
        )
    """)

    op.execute("""
        INSERT INTO exam_record_old (id, exam_id, user_id, status, started_at,
                                     submitted_at, total_score, created_at, updated_at)
        SELECT id, exam_id, 0, status, started_at, submitted_at, score, created_at, updated_at
        FROM exam_record
    """)

    op.execute("DROP TABLE exam_record")
    op.execute("ALTER TABLE exam_record_old RENAME TO exam_record")
    op.execute("CREATE INDEX ix_exam_record_exam_id ON exam_record (exam_id)")
    op.execute("CREATE INDEX ix_exam_record_user_id ON exam_record (user_id)")
