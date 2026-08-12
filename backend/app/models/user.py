"""
用户模型

角色定义：
- admin: 系统管理员，全权限
- hr: HR 角色，管理考试、查看成绩、查看 AI 报告
- employee: 员工角色，参加考试、查看个人结果
- candidate: 旧角色名（向后兼容，等同 employee）
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

VALID_ROLES = ("admin", "hr", "employee", "candidate")
VALID_STATUSES = ("active", "disabled", "pending")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("admin", "candidate", "hr", "employee", name="user_role"),
        nullable=False,
        default="employee",
    )
    status: Mapped[str] = mapped_column(
        Enum(*VALID_STATUSES, name="user_status"),
        nullable=False,
        default="active",
        server_default="active",
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exams = relationship("Exam", back_populates="creator")
    exam_templates = relationship("ExamTemplate", back_populates="creator")
    exam_participants = relationship("ExamParticipant", back_populates="user")

    @property
    def effective_role(self) -> str:
        """向后兼容：candidate 角色等同 employee"""
        return "employee" if self.role == "candidate" else self.role

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
