"""
权限模块
提供角色校验等权限控制依赖
"""
from __future__ import annotations

from fastapi import Depends

from app.core.dependencies import get_current_user
from app.exceptions import ForbiddenException
from app.models.user import User


def require_roles(allowed_roles: list[str]):
    """角色校验依赖工厂：要求当前用户属于指定角色之一"""
    allowed_set = set(allowed_roles)

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_set:
            raise ForbiddenException(
                f"需要 {allowed_roles} 角色，当前为 '{current_user.role}'"
            )
        return current_user

    return _check


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户为管理员角色"""
    if current_user.role != "admin":
        raise ForbiddenException("需要管理员权限")
    return current_user


def require_hr_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户为 HR 或管理员角色"""
    if current_user.role not in ("hr", "admin"):
        raise ForbiddenException("需要 HR 或管理员权限")
    return current_user


def require_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """要求已登录（所有已激活角色均可）"""
    return current_user
