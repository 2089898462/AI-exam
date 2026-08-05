"""
数据库初始化
创建所有表
"""
from app.db.base import Base
from app.db.session import engine


def init_db():
    """创建所有未存在的表"""
    Base.metadata.create_all(bind=engine)