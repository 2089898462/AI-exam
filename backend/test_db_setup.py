import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from app.db.base import Base
from app.models import Exam, Question, User, ExamRecord, AnswerRecord, AiReport

print('Tables before create_all:', list(Base.metadata.tables.keys()))

engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result]
    print('Tables in DB:', tables)
    assert len(tables) == 6, f"Expected 6 tables, got {len(tables)}: {tables}"

print("SUCCESS: All 6 tables created")
