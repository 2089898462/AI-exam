"""
候选人分析报告模型
存储 AI 生成的候选人能力分析报告
AI 只提供辅助分析，不参与招聘决策
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateAnalysisReport(Base):
    __tablename__ = "candidate_analysis_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 关联考试记录
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_record.id"), nullable=False, index=True
    )
    # 关联考试参与人员
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_participant.id"), nullable=True, index=True
    )
    # 关联系统用户（如果候选人是系统用户）
    candidate_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"), nullable=True, index=True
    )

    # 报告摘要
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # 能力维度分析（JSON 存储）
    knowledge_mastery: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weak_points: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 面试建议（JSON 存储）
    interview_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_questions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI 分析元数据
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analysis_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # 报告状态
    status: Mapped[str] = mapped_column(
        Enum("pending", "generated", "reviewed", name="analysis_report_status"),
        nullable=False,
        default="pending",
    )

    # 审核信息
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hr_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return (
            f"<CandidateAnalysisReport(id={self.id}, exam_record_id={self.exam_record_id}, "
            f"overall_score={self.overall_score}, status={self.status})>"
        )
