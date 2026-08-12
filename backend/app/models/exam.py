"""
考试模型
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Exam(Base):
    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", "closed", name="exam_status"),
        nullable=False,
        default="draft",
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    creator = relationship("User", back_populates="exams")
    questions = relationship(
        "Question", back_populates="exam", cascade="all, delete-orphan"
    )
    exam_records = relationship(
        "ExamRecord", back_populates="exam", cascade="all, delete-orphan"
    )
    score_rules = relationship(
        "QuestionScoreRule", back_populates="exam", cascade="all, delete-orphan"
    )
    participants = relationship(
        "ExamParticipant", back_populates="exam", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Exam(id={self.id}, title={self.title}, status={self.status})>"