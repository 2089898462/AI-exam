"""
用户 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


# ============================================================
# 请求
# ============================================================
class UserCreate(BaseSchema):
    """创建用户请求"""
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="candidate", pattern="^(admin|candidate)$")


class UserUpdate(BaseSchema):
    """更新用户请求"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


# ============================================================
# 响应
# ============================================================
class UserResponse(BaseSchema):
    """用户响应"""
    id: int
    username: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseSchema):
    """登录请求"""
    username: str
    password: str