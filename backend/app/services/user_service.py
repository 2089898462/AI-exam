"""
用户服务
"""
from sqlalchemy.orm import Session

from app.exceptions import BusinessException
from app.models.user import User
from app.services.base import BaseService
from app.utils.password import hash_password, verify_password


class UserService(BaseService[User]):
    """用户业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_username(self, username: str) -> User | None:
        """按用户名查询"""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> User | None:
        """按邮箱查询"""
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, username: str, password: str, **kwargs) -> User:
        """创建用户（含重复检查 + 密码哈希）"""
        if self.get_by_username(username):
            raise BusinessException(f"用户名 '{username}' 已存在")

        return self.create(
            username=username,
            password_hash=hash_password(password),
            **kwargs,
        )

    def authenticate(self, username: str, password: str) -> User | None:
        """用户认证"""
        user = self.get_by_username(username)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user