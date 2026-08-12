"""
AI 评分记录模型
独立记录 AI 评分建议，不直接修改 AnswerRecord.score
AI 只提供评分建议，最终成绩必须由 HR 确认
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIScoreRecord(Base):
    __tablename__ = "ai_score_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    answer_record_id: Mapped[int] = mapped_column(
        ForeignKey("answer_record.id"), nullable=False, index=True
    )

    # AI 评分建议
    ai_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_reason: Mapped[str] = mapped_column(Text, nullable=False)

    # 知识点分析
    matched_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_points: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 置信度
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # AI 模型信息
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # 评分依据版本（关联知识库）
    scoring_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("scoring_template.id"), nullable=True
    )
    scoring_rule_versions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 审核状态
    review_status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "ai_scored",
            "hr_confirmed",
            "completed",
            "rejected",
            name="ai_score_review_status",
        ),
        nullable=False,
        default="pending",
    )

    # HR 审核信息
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hr_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 最终确认分数（HR 可以调整）
    confirmed_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    answer_record = relationship("AnswerRecord")
    reviewer = relationship("User")

    def __repr__(self):
        return (
            f"<AIScoreRecord(id={self.id}, answer_record_id={self.answer_record_id}, "
            f"ai_score={self.ai_score}, review_status={self.review_status})>"
        )
