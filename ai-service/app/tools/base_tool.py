"""
Tool 基类（S5.2 增强版）

定义 AI Agent 可调用工具的标准接口。
所有 Tool 必须继承 BaseTool 并实现 execute 方法。

S5.2 增强：
- 标准化返回格式（success/data/message/trace_id）
- 参数类型校验（string/integer/boolean）
- 参数范围校验（min/max/enum）
- 统一异常分类
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string / integer / boolean / number
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None


@dataclass
class ToolResult:
    """统一的工具执行结果（S5.2 标准化格式）

    标准格式：
    {
        "success": true/false,
        "data": {...},
        "message": "描述信息",
        "error": "错误信息（仅失败时）",
        "error_code": "错误码（仅失败时）",
        "tool_name": "工具名称",
        "latency_ms": 123.45,
        "trace_id": "链路追踪ID"
    }
    """
    success: bool
    data: Any = None
    message: str = ""
    error: str | None = None
    error_code: str | None = None
    tool_name: str = ""
    latency_ms: float = 0.0
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "tool_name": self.tool_name,
            "latency_ms": round(self.latency_ms, 2),
            "trace_id": self.trace_id,
        }
        if not self.success:
            result["error"] = self.error
            result["error_code"] = self.error_code
        return result


class BaseTool(ABC):
    """工具基类（S5.2 增强版）

    所有 AI Agent 可调用的工具必须继承此类。

    增强能力：
    - 参数类型校验
    - 参数范围校验
    - 标准化错误码
    """

    # 工具元信息（子类必须覆盖）
    name: str = ""
    description: str = ""
    parameters: list[ToolParameter] = field(default_factory=list)
    # 安全等级：readonly（只读）/ readwrite（读写，AI 禁止使用）
    safety_level: str = "readonly"

    def __init__(self):
        if not self.name:
            raise ValueError("Tool 必须定义 name")
        if not self.description:
            raise ValueError("Tool 必须定义 description")

    @abstractmethod
    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        """执行工具调用

        Args:
            params: 工具参数
            user_id: 调用用户 ID（用于权限校验）
            role: 用户角色
            trace_id: 链路追踪 ID

        Returns:
            ToolResult: 执行结果
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> tuple[bool, str]:
        """校验参数（S5.2 增强版）

        校验内容：
        1. 必填参数检查
        2. 未知参数拒绝
        3. 参数类型检查
        4. 参数范围检查（min/max/enum/length）

        Returns:
            tuple[bool, str]: (是否通过, 错误信息)
        """
        param_map = {p.name: p for p in self.parameters}

        # 1. 必填参数检查
        for name, param_def in param_map.items():
            if param_def.required and name not in params:
                return False, f"缺少必填参数: {name}"

        # 2. 未知参数检查
        for key in params:
            if key not in param_map:
                return False, f"未知参数: {key}"

        # 3. 类型和范围检查
        for name, value in params.items():
            param_def = param_map.get(name)
            if param_def is None or value is None:
                continue

            # 类型检查
            type_ok, type_err = self._check_type(value, param_def.type, name)
            if not type_ok:
                return False, type_err

            # 范围检查
            range_ok, range_err = self._check_range(value, param_def, name)
            if not range_ok:
                return False, range_err

        return True, ""

    def _check_type(self, value: Any, expected_type: str, name: str) -> tuple[bool, str]:
        """检查参数类型"""
        if expected_type == "integer":
            if not isinstance(value, int):
                return False, f"参数 {name} 必须为整数"
        elif expected_type == "string":
            if not isinstance(value, str):
                return False, f"参数 {name} 必须为字符串"
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return False, f"参数 {name} 必须为布尔值"
        elif expected_type == "number":
            if not isinstance(value, (int, float)):
                return False, f"参数 {name} 必须为数字"
        return True, ""

    def _check_range(self, value: Any, param_def: ToolParameter, name: str) -> tuple[bool, str]:
        """检查参数范围"""
        # 枚举检查
        if param_def.enum and value not in param_def.enum:
            return False, f"参数 {name} 必须为 {param_def.enum} 之一"

        # 数值范围
        if isinstance(value, (int, float)):
            if param_def.min_value is not None and value < param_def.min_value:
                return False, f"参数 {name} 不能小于 {param_def.min_value}"
            if param_def.max_value is not None and value > param_def.max_value:
                return False, f"参数 {name} 不能大于 {param_def.max_value}"

        # 字符串长度
        if isinstance(value, str):
            if param_def.min_length is not None and len(value) < param_def.min_length:
                return False, f"参数 {name} 长度不能小于 {param_def.min_length}"
            if param_def.max_length is not None and len(value) > param_def.max_length:
                return False, f"参数 {name} 长度不能大于 {param_def.max_length}"

        return True, ""

    def get_schema(self) -> dict[str, Any]:
        """获取工具的 JSON Schema 描述（供 LLM 函数调用使用）"""
        properties = {}
        required = []

        for p in self.parameters:
            prop = {
                "type": p.type,
                "description": p.description,
            }
            if p.default is not None:
                prop["default"] = p.default
            if p.enum:
                prop["enum"] = p.enum
            if p.min_value is not None:
                prop["minimum"] = p.min_value
            if p.max_value is not None:
                prop["maximum"] = p.max_value
            if p.min_length is not None:
                prop["minLength"] = p.min_length
            if p.max_length is not None:
                prop["maxLength"] = p.max_length
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _make_result(
        self,
        success: bool,
        data: Any = None,
        message: str = "",
        error: str | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
        start_time: float | None = None,
    ) -> ToolResult:
        """创建标准化 ToolResult"""
        latency = (time.time() - start_time) * 1000 if start_time else 0.0
        return ToolResult(
            success=success,
            data=data,
            message=message,
            error=error,
            error_code=error_code,
            tool_name=self.name,
            latency_ms=latency,
            trace_id=trace_id,
        )
