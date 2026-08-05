"""
公共 Schema
分页、通用请求/响应模型
"""
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ============================================================
# 基础 Schema
# ============================================================
class BaseSchema(BaseModel):
    """所有 Schema 的基类，可在此统一配置"""

    model_config = {"from_attributes": True}


class DateTimeMixin(BaseSchema):
    """时间戳混入"""
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================
# 分页
# ============================================================
class PaginationParams(BaseModel):
    """分页查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PaginatedData(BaseModel, Generic[T]):
    """分页响应数据"""
    items: list[T]
    total: int
    page: int
    page_size: int


# ============================================================
# 通用响应
# ============================================================
class ApiResult(BaseModel, Generic[T]):
    """通用 API 响应模型（用于文档生成）"""
    code: int
    message: str
    data: Optional[T] = None