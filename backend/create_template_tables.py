"""
创建模板相关数据库表
"""
import sys
sys.path.insert(0, '.')

from app.db.session import _get_engine
from sqlalchemy import text

engine = _get_engine()

with engine.connect() as conn:
    # 创建 exam_template 表
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS exam_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY (created_by) REFERENCES user(id)
        )
    '''))
    print("1. exam_template 表创建成功")
    
    # 创建 template_question 表
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS template_question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_no VARCHAR(20),
            category VARCHAR(50),
            type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            options JSON,
            answer TEXT NOT NULL,
            score NUMERIC(5, 2) NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY (template_id) REFERENCES exam_template(id)
        )
    '''))
    print("2. template_question 表创建成功")
    
    # 检查answer_record是否有question_snapshot字段
    result = conn.execute(text('PRAGMA table_info(answer_record)'))
    columns = [row[1] for row in result]
    if 'question_snapshot' not in columns:
        try:
            conn.execute(text('ALTER TABLE answer_record ADD COLUMN question_snapshot JSON'))
            print("3. answer_record.question_snapshot 字段添加成功")
        except Exception as e:
            print(f"3. 添加question_snapshot字段失败: {e}")
            # SQLite不支持ALTER TABLE ADD COLUMN，需要使用其他方式
            # 这里我们只是记录，实际使用时可以通过其他方式处理
    else:
        print("3. answer_record.question_snapshot 字段已存在")
    
    conn.commit()
    
    # 验证
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='exam_template'"))
    tables = [row[0] for row in result]
    print(f"\n验证:")
    print(f"  exam_template: {'存在' if len(tables) > 0 else '不存在'}")
    
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='template_question'"))
    tables = [row[0] for row in result]
    print(f"  template_question: {'存在' if len(tables) > 0 else '不存在'}")
    
    result = conn.execute(text('PRAGMA table_info(answer_record)'))
    columns = [row[1] for row in result]
    print(f"  question_snapshot: {'存在' if 'question_snapshot' in columns else '不存在'}")
    
print("\n数据库表创建完成!")
