"""
评分记录模型
跟踪考试评分过程和结果
支持自动评分、AI评分和混合评分模式
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GradingRecord(Base):
    __tablename__ = "grading_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_record.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "grading",
            "completed",
            "failed",
            name="grading_status",
        ),
        nullable=False,
        default="pending",
    )
    grading_type: Mapped[str] = mapped_column(
        Enum("auto", "ai", "hybrid", name="grading_type"),
        nullable=False,
        default="auto",
    )
    total_score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    auto_score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    ai_score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam_record = relationship("ExamRecord", back_populates="grading_record")

    __table_args__ = (
        UniqueConstraint(
            "exam_record_id", name="uq_grading_record_exam_record"
        ),
    )

    def __repr__(self):
        return f"<GradingRecord(id={self.id}, exam_record_id={self.exam_record_id}, status={self.status})>"
