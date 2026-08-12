"""
安全模块
密码哈希、JWT Token 签发与校验

所有配置均来自 app.core.settings，严禁在此文件硬编码敏感信息。

Token 结构：
  Header: {"alg": "HS256", "typ": "JWT"}
  Payload: {"sub": user_id, "role": "hr", "iat": ..., "exp": ..., "type": "access"}
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

SUPPORTED_ROLES = ("admin", "hr", "employee")


def hash_password(password: str) -> str:
    """使用 bcrypt 对明文密码进行哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码是否与哈希匹配"""
    if not hashed_password:
        return False
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
    subject: str | int,
    role: str = "",
    expires_delta: timedelta | None = None,
) -> str:
    """签发 JWT Access Token

    :param subject: 用户 ID
    :param role: 用户角色（admin/hr/employee）
    :param expires_delta: 自定义过期时间
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if role:
        payload["role"] = role
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify_token(token: str) -> dict[str, Any] | None:
    """校验 JWT Token，成功返回 payload，失败返回 None"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_id(token: str) -> int | None:
    """从 Token 中解析用户 ID"""
    payload = verify_token(token)
    if not payload:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


def get_current_user_role(token: str) -> str | None:
    """从 Token 中解析用户角色"""
    payload = verify_token(token)
    if not payload:
        return None
    return payload.get("role")
