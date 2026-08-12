"""
题目评分规则模型
定义不同题型的评分策略和规则
支持按考试定制评分规则
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionScoreRule(Base):
    __tablename__ = "question_score_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id"), nullable=False, index=True
    )
    question_type: Mapped[str] = mapped_column(
        Enum(
            "single_choice",
            "multiple_choice",
            "true_false",
            "short_answer",
            name="rule_question_type",
        ),
        nullable=False,
    )
    score_method: Mapped[str] = mapped_column(
        Enum("auto_compare", "ai_score", "manual", name="score_method"),
        nullable=False,
        default="auto_compare",
    )
    pass_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=1.0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam = relationship("Exam", back_populates="score_rules")

    def __repr__(self):
        return f"<QuestionScoreRule(id={self.id}, exam_id={self.exam_id}, type={self.question_type}, method={self.score_method})>"
