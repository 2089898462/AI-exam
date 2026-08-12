"""
AI 调用审计日志 Service

职责：
- 创建 AI 调用日志
- 更新调用状态
- 查询审计记录（管理员专用）

安全约束：
- 不保存完整敏感数据
- 请求和响应仅保存摘要信息
- 审计查询受权限控制（仅管理员）
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import ForbiddenException
from app.models.ai_call_log import AiCallLog
from app.models.user import User

logger = get_logger(__name__)


class AiCallLogService:
    """AI 调用审计日志业务逻辑"""

    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        trace_id: str,
        caller_user_id: int,
        caller_role: str,
        endpoint: str,
        method: str = "GET",
        source: str = "ai_agent",
        source_id: Optional[str] = None,
        request_summary: Optional[str] = None,
        response_summary: Optional[str] = None,
        status: str = "success",
        http_status: Optional[int] = None,
        error_message: Optional[str] = None,
        latency_ms: Optional[float] = None,
        request_id: Optional[str] = None,
    ) -> AiCallLog:
        """创建 AI 调用日志

        Args:
            trace_id: 链路追踪 ID
            caller_user_id: 调用用户 ID
            caller_role: 调用者角色
            endpoint: 调用的接口路径
            method: HTTP 方法
            source: 调用来源
            source_id: 来源标识
            request_summary: 请求摘要（已脱敏）
            response_summary: 返回摘要（已脱敏）
            status: 状态（success/failed/error）
            http_status: HTTP 状态码
            error_message: 异常信息（已脱敏）
            latency_ms: 调用耗时
            request_id: 请求 ID（关联 Backend 请求）

        Returns:
            AiCallLog: 创建的日志记录
        """
        log = AiCallLog(
            trace_id=trace_id,
            request_id=request_id,
            caller_user_id=caller_user_id,
            caller_role=caller_role,
            source=source,
            source_id=source_id,
            endpoint=endpoint,
            method=method,
            request_summary=self._truncate(request_summary),
            response_summary=self._truncate(response_summary),
            status=status,
            http_status=http_status,
            error_message=self._truncate(error_message, max_length=500),
            latency_ms=latency_ms,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        logger.info(
            f"[AI_CALL_LOG] id={log.id} | trace_id={trace_id} | "
            f"endpoint={endpoint} | status={status} | latency_ms={latency_ms or 0:.1f}"
        )
        return log

    def update_status(
        self,
        log_id: int,
        status: str,
        http_status: Optional[int] = None,
        response_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> AiCallLog:
        """更新调用日志状态

        Args:
            log_id: 日志 ID
            status: 新状态
            http_status: HTTP 状态码
            response_summary: 返回摘要（已脱敏）
            error_message: 异常信息（已脱敏）
            latency_ms: 调用耗时

        Returns:
            AiCallLog: 更新后的日志记录
        """
        log = self.db.query(AiCallLog).filter(AiCallLog.id == log_id).first()
        if not log:
            raise ValueError(f"AI 调用日志不存在: {log_id}")

        log.status = status
        if http_status is not None:
            log.http_status = http_status
        if response_summary is not None:
            log.response_summary = self._truncate(response_summary)
        if error_message is not None:
            log.error_message = self._truncate(error_message, max_length=500)
        if latency_ms is not None:
            log.latency_ms = latency_ms

        self.db.commit()
        self.db.refresh(log)
        return log

    def query_logs(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        caller_user_id: Optional[int] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict:
        """查询 AI 调用日志（管理员专用）

        Args:
            current_user: 当前用户（必须为管理员）
            page: 页码
            page_size: 每页数量
            caller_user_id: 调用者 ID 过滤
            status: 状态过滤
            source: 来源过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            dict: 分页的日志记录
        """
        # 权限检查：仅管理员可查询
        if current_user.role != "admin":
            raise ForbiddenException("仅管理员可查询 AI 调用日志")

        query = self.db.query(AiCallLog)

        if caller_user_id:
            query = query.filter(AiCallLog.caller_user_id == caller_user_id)
        if status:
            query = query.filter(AiCallLog.status == status)
        if source:
            query = query.filter(AiCallLog.source == source)
        if start_time:
            query = query.filter(AiCallLog.called_at >= start_time)
        if end_time:
            query = query.filter(AiCallLog.called_at <= end_time)

        total = query.count()
        logs = query.order_by(AiCallLog.called_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        items = []
        for log in logs:
            item = {
                "id": log.id,
                "trace_id": log.trace_id,
                "request_id": log.request_id,
                "caller_user_id": log.caller_user_id,
                "caller_role": log.caller_role,
                "source": log.source,
                "source_id": log.source_id,
                "endpoint": log.endpoint,
                "method": log.method,
                "request_summary": log.request_summary,
                "response_summary": log.response_summary,
                "status": log.status,
                "http_status": log.http_status,
                "error_message": log.error_message,
                "latency_ms": log.latency_ms,
                "called_at": log.called_at.isoformat() if log.called_at else None,
            }
            items.append(item)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_log_by_id(
        self,
        log_id: int,
        current_user: User,
    ) -> Optional[dict]:
        """获取单条 AI 调用日志（管理员专用）

        Args:
            log_id: 日志 ID
            current_user: 当前用户（必须为管理员）

        Returns:
            Optional[dict]: 日志详情
        """
        if current_user.role != "admin":
            raise ForbiddenException("仅管理员可查询 AI 调用日志")

        log = self.db.query(AiCallLog).filter(AiCallLog.id == log_id).first()
        if not log:
            return None

        return {
            "id": log.id,
            "trace_id": log.trace_id,
            "request_id": log.request_id,
            "caller_user_id": log.caller_user_id,
            "caller_role": log.caller_role,
            "source": log.source,
            "source_id": log.source_id,
            "endpoint": log.endpoint,
            "method": log.method,
            "request_summary": log.request_summary,
            "response_summary": log.response_summary,
            "status": log.status,
            "http_status": log.http_status,
            "error_message": log.error_message,
            "latency_ms": log.latency_ms,
            "called_at": log.called_at.isoformat() if log.called_at else None,
        }

    @staticmethod
    def _truncate(text: Optional[str], max_length: int = 1000) -> Optional[str]:
        """截断文本到指定长度

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            Optional[str]: 截断后的文本
        """
        if text is None:
            return None
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."