"""
考试记录模型
记录候选人参加考试的全过程（候选人非系统用户，采用嵌入式身份信息）
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamRecord(Base):
    __tablename__ = "exam_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id"), nullable=False, index=True
    )
    exam_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_participant.id"), nullable=True, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("not_started", "in_progress", "submitted", "graded", name="record_status"),
        nullable=False,
        default="not_started",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam = relationship("Exam", back_populates="exam_records")
    answer_records = relationship(
        "AnswerRecord", back_populates="exam_record", cascade="all, delete-orphan"
    )
    ai_report = relationship(
        "AiReport", back_populates="exam_record", uselist=False, cascade="all, delete-orphan"
    )
    grading_record = relationship(
        "GradingRecord", back_populates="exam_record", uselist=False, cascade="all, delete-orphan"
    )
    monitor_summary = relationship(
        "ExamMonitorSummary", back_populates="exam_record", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ExamRecord(id={self.id}, exam_id={self.exam_id}, candidate={self.candidate_name}, status={self.status})>"
