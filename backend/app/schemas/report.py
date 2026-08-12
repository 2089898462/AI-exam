"""
AI 报告 Schema
报告生成请求/响应数据模型
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class ReportGenerateRequest(BaseSchema):
    """报告生成请求"""
    exam_record_id: int = Field(..., description="考试记录 ID")
    model_used: str = Field(default="qwen-plus", description="使用的模型")
    prompt_version: str = Field(default="1.0", description="Prompt 版本")


class ReportResponse(BaseSchema):
    """报告响应"""
    id: int
    exam_record_id: int
    summary: Optional[str] = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    skill_analysis: dict = {}
    interview_suggestions: list[str] = []
    recommendation: str = "保留考虑"
    model_used: str
    prompt_version: str
    status: str
    created_at: datetime
    updated_at: datetime


class ReportListItem(BaseSchema):
    """报告列表项"""
    id: int
    exam_record_id: int
    exam_id: int
    exam_title: str
    candidate_name: str
    status: str
    recommendation: str
    created_at: Optional[str] = None


class ReportListResponse(BaseSchema):
    """报告列表响应"""
    items: list[ReportListItem] = []
    total: int
    page: int
    page_size: int


class ReportDetailResponse(BaseSchema):
    """报告详情响应"""
    id: int
    exam_record_id: int
    exam_id: int
    exam_title: str
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    total_score: Optional[float] = None
    auto_score: Optional[float] = None
    ai_score: Optional[float] = None
    passed: Optional[bool] = None
    report: Optional[ReportResponse] = None
