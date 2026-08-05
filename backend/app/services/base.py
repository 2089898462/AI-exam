"""
Service 基类
提供通用的 CRUD 操作模板
"""
from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseService(Generic[ModelType]):
    """基础服务类"""

    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model

    def get(self, id: int) -> ModelType | None:
        """按 ID 查询"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, skip: int = 0, limit: int = 20, **filters
    ) -> list[ModelType]:
        """批量查询"""
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()

    def count(self, **filters) -> int:
        """统计数量"""
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        return query.count()

    def create(self, **kwargs) -> ModelType:
        """创建记录"""
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, id: int, **kwargs) -> ModelType | None:
        """更新记录"""
        obj = self.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        """删除记录"""
        obj = self.get(id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True