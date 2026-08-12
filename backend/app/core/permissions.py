"""
权限模块
提供角色校验等权限控制依赖

角色映射：
- admin: 全权限
- hr: 管理考试、查看成绩和报告
- employee: 员工，参加考试、查看个人结果
- candidate: 向后兼容，等同 employee
"""
from __future__ import annotations

from fastapi import Depends

from app.core.dependencies import get_current_user
from app.exceptions import ForbiddenException
from app.models.user import User


def _normalize_role(role: str) -> str:
    """角色标准化：candidate → employee"""
    return "employee" if role == "candidate" else role


def require_roles(allowed_roles: list[str]):
    """角色校验依赖工厂：要求当前用户属于指定角色之一

    支持 candidate 向后兼容：
    - candidate 自动映射为 employee
    """
    normalized_allowed = {_normalize_role(r) for r in allowed_roles}

    def _check(current_user: User = Depends(get_current_user)) -> User:
        effective = _normalize_role(current_user.role)
        if effective not in normalized_allowed:
            raise ForbiddenException(
                f"需要 {allowed_roles} 角色，当前为 '{current_user.role}'"
            )
        return current_user

    return _check


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户为管理员角色"""
    if _normalize_role(current_user.role) != "admin":
        raise ForbiddenException("需要管理员权限")
    return current_user


def require_hr_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户为 HR 或管理员角色"""
    effective = _normalize_role(current_user.role)
    if effective not in ("hr", "admin"):
        raise ForbiddenException("需要 HR 或管理员权限")
    return current_user


def require_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """要求已登录（所有已激活角色均可）"""
    return current_user
