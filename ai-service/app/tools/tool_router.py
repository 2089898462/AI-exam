"""
Tool Router 模块（S5.2 新增）

职责：
- 接收 AI 工具调用请求
- 权限校验（用户角色 + 工具安全等级）
- 参数校验（调用 Tool 自身的 validate_params）
- 执行调度（从注册表获取工具并执行）
- 审计记录（每次调用记录审计日志）
- 统一异常处理

流程：
AI Agent → Tool Router → 权限校验 → 参数校验 → 执行 → 审计 → 返回

设计原则：
- 统一入口：所有 AI 工具调用必须通过 Tool Router
- 权限前置：权限校验在执行前完成
- 审计必达：每次调用（成功/失败/异常）均记录审计日志
- 异常隔离：单个工具异常不影响其他工具
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger
from app.tools.base_tool import ToolResult
from app.tools.tool_registry import ToolRegistry, get_tool_registry

logger = get_logger(__name__)


# ============================================================
# 权限配置
# ============================================================

# 角色到可用安全等级的映射
ROLE_SAFETY_MAP: dict[str, set[str]] = {
    "admin": {"readonly"},
    "hr": {"readonly"},
    "employee": set(),       # 员工无 AI 工具权限
    "candidate": set(),      # 候选人无 AI 工具权限
}

# 允许使用 AI Agent 的角色
AI_ALLOWED_ROLES = {"admin", "hr"}


@dataclass
class ToolCallAudit:
    """工具调用审计记录"""
    trace_id: str
    tool_name: str
    user_id: int
    role: str
    success: bool
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    params_summary: dict[str, Any] = field(default_factory=dict)
    result_summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "role": self.role,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
            "params_summary": self.params_summary,
            "result_summary": self.result_summary,
            "error": self.error,
            "error_code": self.error_code,
        }


# ============================================================
# Tool Router
# ============================================================

class ToolRouter:
    """工具路由器（S5.2 核心组件）

    统一管理 AI Agent 对 Backend API 的调用。
    所有 AI 工具调用必须通过此类，确保：
    - 权限校验
    - 参数校验
    - 审计记录
    - 异常处理
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self._registry = registry or get_tool_registry()
        self._audit_logs: list[ToolCallAudit] = []
        self._max_audit_logs = 10000  # 内存审计日志上限

    async def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        """调用工具（统一入口）

        完整流程：
        1. 生成/获取 trace_id
        2. 权限校验（角色检查 + 工具安全等级）
        3. 参数校验
        4. 工具执行
        5. 审计记录
        6. 返回结果

        Args:
            tool_name: 工具名称
            params: 工具参数
            user_id: 调用用户 ID
            role: 用户角色
            trace_id: 链路追踪 ID

        Returns:
            ToolResult: 标准化执行结果
        """
        start_time = time.time()
        trace_id = trace_id or str(uuid.uuid4())

        # 1. 获取工具
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            result = ToolResult(
                success=False,
                error=f"工具不存在: {tool_name}",
                error_code="TOOL_NOT_FOUND",
                tool_name=tool_name,
                trace_id=trace_id,
                message=f"工具 {tool_name} 未注册",
            )
            self._record_audit(result, user_id, role, trace_id, params, start_time)
            return result

        # 2. 权限校验
        auth_ok, auth_error = self._check_permission(tool.safety_level, user_id, role)
        if not auth_ok:
            result = ToolResult(
                success=False,
                error=auth_error,
                error_code="PERMISSION_DENIED",
                tool_name=tool_name,
                trace_id=trace_id,
                message="权限校验失败",
            )
            self._record_audit(result, user_id, role, trace_id, params, start_time)
            return result

        # 3. 参数校验
        valid, error_msg = tool.validate_params(params)
        if not valid:
            result = ToolResult(
                success=False,
                error=error_msg,
                error_code="INVALID_PARAMS",
                tool_name=tool_name,
                trace_id=trace_id,
                message="参数校验失败",
            )
            self._record_audit(result, user_id, role, trace_id, params, start_time)
            return result

        # 4. 执行工具
        try:
            result = await tool.execute(
                params=params,
                user_id=user_id,
                role=role,
                trace_id=trace_id,
            )
            # 补充 message
            if not result.message:
                result.message = self._build_message(result)

        except Exception as e:
            logger.error(
                f"[ToolRouter] 工具执行异常: tool={tool_name}, "
                f"error={str(e)}, trace_id={trace_id}"
            )
            result = ToolResult(
                success=False,
                error=f"工具执行异常: {str(e)}",
                error_code="EXECUTION_ERROR",
                tool_name=tool_name,
                trace_id=trace_id,
                message=f"工具 {tool_name} 执行过程中发生异常",
            )

        # 5. 审计记录
        self._record_audit(result, user_id, role, trace_id, params, start_time)

        return result

    def _check_permission(
        self,
        tool_safety_level: str,
        user_id: int,
        role: str,
    ) -> tuple[bool, str]:
        """权限校验

        检查项：
        1. 用户角色是否允许使用 AI Agent
        2. 用户角色是否允许使用该安全等级的工具

        Returns:
            tuple[bool, str]: (是否通过, 错误信息)
        """
        if user_id <= 0:
            return False, "无效的用户身份"

        if role not in AI_ALLOWED_ROLES:
            return False, f"角色 {role} 无权使用 AI 工具"

        allowed_levels = ROLE_SAFETY_MAP.get(role, set())
        if tool_safety_level not in allowed_levels:
            return False, f"角色 {role} 无权使用 {tool_safety_level} 级别的工具"

        return True, ""

    def _build_message(self, result: ToolResult) -> str:
        """根据结果构建描述信息"""
        if result.success:
            if isinstance(result.data, dict):
                # 尝试生成有意义的摘要
                keys = list(result.data.keys())[:3]
                key_desc = ", ".join(keys)
                return f"工具 {result.tool_name} 执行成功，返回字段: {key_desc}"
            else:
                return f"工具 {result.tool_name} 执行成功"
        else:
            return f"工具 {result.tool_name} 执行失败: {result.error}"

    def _record_audit(
        self,
        result: ToolResult,
        user_id: int,
        role: str,
        trace_id: str,
        params: dict[str, Any],
        start_time: float,
    ) -> None:
        """记录审计日志

        S5.2 要求：每次工具调用必须记录审计。
        当前实现：内存记录，后续版本对接 Backend AiCallLog。
        """
        latency_ms = (time.time() - start_time) * 1000

        # 参数摘要（不保存完整参数）
        params_summary = self._summarize_params(params)

        # 结果摘要
        result_summary = {
            "success": result.success,
            "data_preview": str(result.data)[:200] if result.data else None,
        }

        audit = ToolCallAudit(
            trace_id=trace_id,
            tool_name=result.tool_name,
            user_id=user_id,
            role=role,
            success=result.success,
            latency_ms=latency_ms,
            params_summary=params_summary,
            result_summary=result_summary,
            error=result.error,
            error_code=result.error_code,
        )

        self._audit_logs.append(audit)

        # 超过上限时移除最旧记录
        if len(self._audit_logs) > self._max_audit_logs:
            self._audit_logs = self._audit_logs[-self._max_audit_logs:]

        # 日志记录
        log_level = logger.info if result.success else logger.warning
        log_level(
            f"[ToolRouter] 工具调用: tool={result.tool_name}, "
            f"user={user_id}, success={result.success}, "
            f"latency={latency_ms:.1f}ms, trace_id={trace_id}"
        )

    def _summarize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """参数摘要（脱敏处理，不保存敏感数据）"""
        summary = {}
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 100:
                summary[key] = value[:100] + "..."
            else:
                summary[key] = value
        return summary

    # ========================================================
    # 审计日志查询
    # ========================================================

    def get_audit_logs(
        self,
        tool_name: str | None = None,
        user_id: int | None = None,
        success: bool | None = None,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """查询审计日志

        Args:
            tool_name: 按工具名筛选
            user_id: 按用户筛选
            success: 按成功/失败筛选
            trace_id: 按 trace_id 筛选
            limit: 返回条数

        Returns:
            审计日志列表（最新在前）
        """
        logs = self._audit_logs

        if tool_name:
            logs = [l for l in logs if l.tool_name == tool_name]
        if user_id is not None:
            logs = [l for l in logs if l.user_id == user_id]
        if success is not None:
            logs = [l for l in logs if l.success == success]
        if trace_id:
            logs = [l for l in logs if l.trace_id == trace_id]

        # 最新在前
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)
        return [l.to_dict() for l in logs[:limit]]

    def get_audit_log_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        """按 trace_id 查询审计日志"""
        for log in self._audit_logs:
            if log.trace_id == trace_id:
                return log.to_dict()
        return None

    def clear_audit_logs(self) -> None:
        """清空审计日志（仅用于测试）"""
        self._audit_logs.clear()

    def list_available_tools(
        self,
        user_id: int,
        role: str,
    ) -> list[dict[str, Any]]:
        """获取当前用户可用的工具列表"""
        if role not in AI_ALLOWED_ROLES:
            return []

        tools = []
        for tool in self._registry.get_all_tools().values():
            if tool.safety_level in ROLE_SAFETY_MAP.get(role, set()):
                tools.append(tool.get_schema())
        return tools


# 全局 ToolRouter 实例
_tool_router: ToolRouter | None = None


def get_tool_router() -> ToolRouter:
    """获取全局 ToolRouter 实例"""
    global _tool_router
    if _tool_router is None:
        _tool_router = ToolRouter()
    return _tool_router
