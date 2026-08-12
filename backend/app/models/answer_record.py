"""
答题记录模型
记录候选人每一道题的答案和评分
支持题目快照机制，确保历史数据隔离
支持 AI 评分状态管理
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnswerRecord(Base):
    __tablename__ = "answer_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_record.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id"), nullable=False, index=True
    )
    answer_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score_level: Mapped[str | None] = mapped_column(
        Enum("full_correct", "partial_correct", "incorrect", name="score_level"),
        nullable=True,
        default=None,
        comment="评分等级：完全正确/部分正确/错误",
    )
    
    # AI 评分相关字段
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # AI 评分状态管理
    ai_status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed", name="ai_scoring_status"),
        nullable=False,
        default="pending",
    )
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 知识点分析（JSON 格式存储）
    knowledge_points: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    matched_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    
    # 题目快照字段 - 确保历史数据隔离
    question_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam_record = relationship("ExamRecord", back_populates="answer_records")
    question = relationship("Question", back_populates="answer_records")

    # 约束：同一次考试记录中，一道题只能有一条答案
    __table_args__ = (
        UniqueConstraint(
            "exam_record_id",
            "question_id",
            name="uq_answer_record_question",
        ),
    )

    def __repr__(self):
        return f"<AnswerRecord(id={self.id}, exam_record_id={self.exam_record_id}, question_id={self.question_id})>"
