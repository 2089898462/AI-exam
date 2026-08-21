"""
考试监考汇总模型
记录每场考试的监考统计数据（异常行为汇总）
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamMonitorSummary(Base):
    __tablename__ = "exam_monitor_summary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_record.id"), nullable=False, unique=True, index=True
    )
    leave_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="累计离开时长(秒)")
    risk_level: Mapped[str] = mapped_column(
        Enum("normal", "low", "medium", "high", name="risk_level"),
        nullable=False,
        default="normal",
    )
    detail_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="详细事件列表(JSON格式)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    exam_record = relationship("ExamRecord", back_populates="monitor_summary", uselist=False)

    def __repr__(self):
        return f"<ExamMonitorSummary(id={self.id}, record_id={self.exam_record_id}, risk={self.risk_level})>"
