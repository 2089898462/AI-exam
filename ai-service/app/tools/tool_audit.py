"""
Tool 审计模块（S5.2 新增）

提供 AI Tool 调用的审计日志查询能力。
与 S4.4-C1 的 AiCallLog 体系兼容。

当前实现：
- 内存审计日志（由 ToolRouter 记录）
- 支持按 trace_id / tool_name / user_id 查询

后续集成：
- 对接 Backend AiCallLog API
- 持久化审计日志
"""
from __future__ import annotations

from typing import Any

from app.tools.tool_router import ToolRouter, ToolCallAudit, get_tool_router


class ToolAuditService:
    """工具调用审计服务

    提供审计日志的查询和管理能力。
    """

    def __init__(self, router: ToolRouter | None = None):
        self._router = router or get_tool_router()

    def query_logs(
        self,
        tool_name: str | None = None,
        user_id: int | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """查询审计日志

        Args:
            tool_name: 按工具名筛选
            user_id: 按用户筛选
            success: 按成功/失败筛选
            limit: 返回条数

        Returns:
            dict: {
                "total": 总数,
                "filtered": 筛选后数量,
                "logs": 日志列表
            }
        """
        logs = self._router.get_audit_logs(
            tool_name=tool_name,
            user_id=user_id,
            success=success,
            limit=limit,
        )

        # 统计信息
        total = len(self._router._audit_logs)
        success_count = sum(1 for l in self._router._audit_logs if l.success)
        fail_count = total - success_count

        return {
            "total": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "logs": logs,
        }

    def query_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        """按 trace_id 查询单次调用的完整审计"""
        return self._router.get_audit_log_by_trace_id(trace_id)

    def get_tool_usage_stats(self) -> dict[str, Any]:
        """获取工具使用统计"""
        logs = self._router._audit_logs

        tool_stats: dict[str, dict[str, Any]] = {}
        for log in logs:
            if log.tool_name not in tool_stats:
                tool_stats[log.tool_name] = {
                    "total_calls": 0,
                    "success_calls": 0,
                    "fail_calls": 0,
                    "total_latency_ms": 0.0,
                }
            stats = tool_stats[log.tool_name]
            stats["total_calls"] += 1
            if log.success:
                stats["success_calls"] += 1
            else:
                stats["fail_calls"] += 1
            stats["total_latency_ms"] += log.latency_ms

        # 计算平均延迟
        for stats in tool_stats.values():
            stats["avg_latency_ms"] = round(
                stats["total_latency_ms"] / max(stats["total_calls"], 1), 2
            )
            del stats["total_latency_ms"]

        return {
            "total_calls": len(logs),
            "tool_stats": tool_stats,
        }

    def get_recent_failures(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取最近的失败调用"""
        return self._router.get_audit_logs(
            success=False,
            limit=limit,
        )


def get_tool_audit_service() -> ToolAuditService:
    """获取全局审计服务实例"""
    return ToolAuditService()
