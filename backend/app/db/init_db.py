"""
数据库初始化
创建所有表
"""
from app.db.base import Base
from app.db.session import _get_engine
import app.models  # noqa: F401 - 确保所有模型被加载到 Base.metadata


def init_db():
    """创建所有未存在的表"""
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)