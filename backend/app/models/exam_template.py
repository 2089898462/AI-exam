"""
试卷模板模型
用于创建固定试卷模板，支持基于模板快速创建考试
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamTemplate(Base):
    __tablename__ = "exam_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="template_status"),
        nullable=False,
        default="active",
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    creator = relationship("User", back_populates="exam_templates")
    template_questions = relationship(
        "TemplateQuestion", back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateQuestion.sort_order"
    )

    def __repr__(self):
        return f"<ExamTemplate(id={self.id}, name={self.name}, status={self.status})>"
