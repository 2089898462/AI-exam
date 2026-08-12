"""
数据库会话管理

注意：engine 为懒加载，首次使用时才创建。
这样可以确保：
1. 测试时可以在 import 之后覆盖 DATABASE_URL
2. 启动时 .env 文件有机会被加载
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        if not db_url:
            db_url = "sqlite:///./exam_system.db"
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(db_url, connect_args=connect_args)
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine()
        )
    return _SessionLocal


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
