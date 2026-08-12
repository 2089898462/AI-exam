"""
认证服务
负责登录校验、Token 生成、当前用户解析
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.exceptions import BusinessException, UnauthorizedException
from app.models.user import User

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(
        self,
        username: str,
        password: str,
        display_name: str,
        email: str | None = None,
        phone: str | None = None,
        role: str = "candidate",
    ) -> User:
        from app.services.user_service import UserService

        user_service = UserService(self.db)
        if user_service.get_by_username(username):
            logger.warning(f"注册失败：用户名 '{username}' 已存在")
            raise BusinessException(f"用户名 '{username}' 已存在")
        if email and user_service.get_by_email(email):
            logger.warning(f"注册失败：邮箱 '{email}' 已被注册")
            raise BusinessException(f"邮箱 '{email}' 已注册")

        user = user_service.create_user(
            username=username,
            password=password,
            display_name=display_name,
            email=email,
            phone=phone,
            role=role,
        )
        logger.info(f"用户注册成功: user_id={user.id}, username={username}, role={role}")
        return user

    def login(self, username: str, password: str) -> dict:
        _start = time.perf_counter()
        user = self._authenticate(username, password)
        if not user:
            logger.warning(f"登录失败：用户名或密码错误, username={username}")
            raise UnauthorizedException("用户名或密码错误")
        if not user.is_active:
            logger.warning(f"登录失败：账号已被禁用, user_id={user.id}")
            raise UnauthorizedException("账号已被禁用，请联系管理员")

        access_token = create_access_token(subject=user.id, role=user.role)
        elapsed = (time.perf_counter() - _start) * 1000
        logger.info(
            f"登录成功: user_id={user.id}, username={username}, "
            f"role={user.role}, elapsed_ms={elapsed:.1f}"
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 60 * 60,
            "user": self._serialize_user(user),
        }

    def get_current_user(self, token: str) -> User:
        user_id = get_current_user_id(token)
        if not user_id:
            raise UnauthorizedException("登录状态已失效，请重新登录")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise UnauthorizedException("用户不存在或已被禁用")
        return user

    def _authenticate(self, username: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
        }
