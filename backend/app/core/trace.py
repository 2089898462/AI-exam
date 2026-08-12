"""
链路追踪（trace_id）模块

建立统一的 trace_id 机制，贯穿：
Frontend → Backend API → Service → Log → AI 调用

与现有 request_id 的关系：
- request_id：标识单次 HTTP 请求（已有）
- trace_id：标识完整调用链路（新增）
- 两者在入口处生成，记录在所有日志中

传递规则：
1. 请求进入时生成 trace_id
2. trace_id 存入 request.state
3. 所有日志自动携带 trace_id
4. AI 调用日志关联 trace_id
"""
from __future__ import annotations

import uuid
from typing import Optional


def generate_trace_id() -> str:
    """生成唯一的 trace_id

    使用 UUID4，保证全局唯一性
    """
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """生成唯一的 request_id"""
    return str(uuid.uuid4())


# 别名，方便统一导入
new_trace_id = generate_trace_id
new_request_id = generate_request_id


class TraceContext:
    """链路追踪上下文

    用于在 Service 层传递 trace_id
    """

    def __init__(self, trace_id: str, request_id: Optional[str] = None):
        self.trace_id = trace_id
        self.request_id = request_id or trace_id

    def __repr__(self) -> str:
        return f"TraceContext(trace_id={self.trace_id}, request_id={self.request_id})"

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }