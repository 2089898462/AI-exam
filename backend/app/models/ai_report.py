"""
AI 报告模型
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AiReport(Base):
    __tablename__ = "ai_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_record.id"), nullable=False, unique=True
    )
    strengths: Mapped[dict] = mapped_column(JSON, nullable=False)
    weaknesses: Mapped[dict] = mapped_column(JSON, nullable=False)
    learning_suggestions: Mapped[dict] = mapped_column(JSON, nullable=False)
    raw_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam_record = relationship("ExamRecord", back_populates="ai_report")

    __table_args__ = (
        UniqueConstraint(
            "exam_record_id", name="uq_ai_report_exam_record"
        ),
    )

    def __repr__(self):
        return f"<AiReport(id={self.id}, exam_record_id={self.exam_record_id})>"