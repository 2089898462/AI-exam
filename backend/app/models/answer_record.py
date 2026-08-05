"""
答题记录模型
记录候选人每一道题的答案和评分
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
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
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
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
