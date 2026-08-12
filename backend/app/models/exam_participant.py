"""
考试参与人员模型
用于管理考试与参与人员之间的关系
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamParticipant(Base):
    __tablename__ = "exam_participant"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"), nullable=True, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("assigned", "not_started", "in_progress", "submitted", "completed", name="participant_status"),
        nullable=False,
        default="assigned",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam = relationship("Exam", back_populates="participants")
    user = relationship("User", back_populates="exam_participants")

    # 唯一约束：同一考试中候选人姓名+电话/邮箱不能重复
    __table_args__ = (
        UniqueConstraint("exam_id", "candidate_phone", name="uq_exam_participant_phone"),
    )

    def __repr__(self):
        return f"<ExamParticipant(id={self.id}, exam_id={self.exam_id}, name={self.candidate_name}, status={self.status})>"
