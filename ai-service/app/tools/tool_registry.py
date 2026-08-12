"""
Tool 注册表

集中管理所有 AI Agent 可调用的工具。
提供工具注册、查询、执行等功能。

设计原则：
- 只读工具优先（AI 只能查询，不能修改）
- 工具必须经过注册才能使用
- 支持按用户角色过滤可用工具
"""
from __future__ import annotations

from typing import Any

from app.tools.base_tool import BaseTool, ToolResult


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        if tool.name in self._tools:
            raise ValueError(f"工具已注册: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        if tool_name not in self._tools:
            raise ValueError(f"工具不存在: {tool_name}")
        del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """获取工具"""
        return self._tools.get(tool_name)

    def list_tools(
        self,
        user_id: int | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出可用工具（供 LLM 选择）"""
        tools = []
        for tool in self._tools.values():
            # AI 只能使用只读工具
            if tool.safety_level != "readonly":
                continue
            tools.append(tool.get_schema())
        return tools

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        """执行工具调用

        Args:
            tool_name: 工具名称
            params: 工具参数
            user_id: 用户 ID
            role: 用户角色
            trace_id: 链路追踪 ID

        Returns:
            ToolResult: 执行结果
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"工具不存在: {tool_name}",
                error_code="TOOL_NOT_FOUND",
                tool_name=tool_name,
            )

        # 安全检查：AI 只能使用只读工具
        if tool.safety_level != "readonly":
            return ToolResult(
                success=False,
                error=f"AI 无权调用写操作工具: {tool_name}",
                error_code="PERMISSION_DENIED",
                tool_name=tool_name,
            )

        # 参数校验
        valid, error_msg = tool.validate_params(params)
        if not valid:
            return ToolResult(
                success=False,
                error=error_msg,
                error_code="INVALID_PARAMS",
                tool_name=tool_name,
            )

        # 执行
        return await tool.execute(
            params=params,
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

    def get_all_tools(self) -> dict[str, BaseTool]:
        """获取所有已注册工具"""
        return dict(self._tools)


# 全局工具注册表实例
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
