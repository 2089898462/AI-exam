"""
AI 调用审计日志模型

用于记录 AI Agent 的调用行为，支持：
- 调用用户 / 时间 / 接口 / 来源
- 请求摘要 / 返回摘要
- 状态 / 异常信息
- trace_id 链路追踪

安全约束：
- 不保存完整敏感数据（手机号、邮箱、完整答案）
- 请求和响应仅保存摘要信息
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiCallLog(Base):
    """AI 调用审计日志"""

    __tablename__ = "ai_call_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="链路追踪 ID"
    )
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=True, index=True, comment="请求 ID（关联 Backend 请求）"
    )

    # 调用者信息
    caller_user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="调用用户 ID"
    )
    caller_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="admin", comment="调用者角色"
    )

    # 调用来源
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ai_agent", comment="调用来源（ai_agent / webhook / api）"
    )
    source_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="来源标识（如 Agent 名称）"
    )

    # 接口信息
    endpoint: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="调用的接口路径"
    )
    method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="GET", comment="HTTP 方法"
    )

    # 请求/响应摘要
    request_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="请求摘要（已脱敏，不含敏感数据）"
    )
    response_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="返回摘要（已脱敏，不含敏感数据）"
    )

    # 调用结果
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success", index=True,
        comment="状态：success / failed / error"
    )
    http_status: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="HTTP 状态码"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="异常信息（脱敏后）"
    )
    latency_ms: Mapped[float | None] = mapped_column(
        nullable=True, comment="调用耗时（毫秒）"
    )

    # 时间戳
    called_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True,
        comment="调用时间"
    )

    # 复合索引
    __table_args__ = (
        Index("ix_ai_call_log_trace_id_called_at", "trace_id", "called_at"),
        Index("ix_ai_call_log_caller_status", "caller_user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AiCallLog(id={self.id}, trace_id={self.trace_id}, endpoint={self.endpoint}, status={self.status})>"