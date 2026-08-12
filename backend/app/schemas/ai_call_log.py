"""
AI 调用审计日志 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AiCallLogItem(BaseModel):
    """AI 调用日志项"""
    id: int
    trace_id: str
    request_id: Optional[str] = None
    caller_user_id: int
    caller_role: str
    source: str
    source_id: Optional[str] = None
    endpoint: str
    method: str
    request_summary: Optional[str] = None
    response_summary: Optional[str] = None
    status: str
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    called_at: Optional[str] = None


class AiCallLogListResponse(BaseModel):
    """AI 调用日志列表响应"""
    items: list[AiCallLogItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class AiCallLogQueryParams(BaseModel):
    """AI 调用日志查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    caller_user_id: Optional[int] = Field(default=None, description="调用者 ID")
    status: Optional[str] = Field(default=None, description="状态：success/failed/error")
    source: Optional[str] = Field(default=None, description="来源：ai_agent/webhook/api")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")