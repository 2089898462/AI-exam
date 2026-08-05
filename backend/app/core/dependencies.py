"""
应用依赖模块
提供 FastAPI 依赖注入所需的公共依赖
"""
from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.exceptions import UnauthorizedException
from app.models.user import User


def _extract_token(authorization: str | None) -> str:
    """从 Authorization 头中提取 Bearer Token"""
    if not authorization:
        raise UnauthorizedException("缺少 Authorization 头")
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Token 格式错误，应为 'Bearer <token>'")
    token = parts[1].strip()
    if not token:
        raise UnauthorizedException("Token 不能为空")
    return token


def get_current_user_id_from_header(
    authorization: str | None = Header(default=None),
) -> int:
    """从 Authorization 头解析当前用户 ID（轻量依赖，不查库）"""
    token = _extract_token(authorization)
    user_id = get_current_user_id(token)
    if not user_id:
        raise UnauthorizedException("登录状态已失效，请重新登录")
    return user_id


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """解析 Token 并加载当前用户实体（必须登录）"""
    token = _extract_token(authorization)
    user_id = get_current_user_id(token)
    if not user_id:
        raise UnauthorizedException("登录状态已失效，请重新登录")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise UnauthorizedException("用户不存在或已被禁用")
    return user


def get_optional_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """可选鉴权：有 Token 就解析，没有则返回 None"""
    if not authorization:
        return None
    token = _extract_token(authorization)
    user_id = get_current_user_id(token)
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user
