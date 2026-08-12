"""
AI 阅卷 API Schema
AI 评分建议、查询、确认的请求/响应数据模型
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class TriggerAIScoringRequest(BaseSchema):
    """发起 AI 评分请求"""
    answer_record_id: int = Field(..., description="答题记录 ID")


class AIScoreResponse(BaseSchema):
    """AI 评分记录响应"""
    id: int
    answer_record_id: int
    ai_score: float
    max_score: float
    score_reason: str
    matched_points: Optional[str] = None
    missing_points: Optional[str] = None
    confidence: float
    model_name: Optional[str] = None
    prompt_version: str
    review_status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    hr_remark: Optional[str] = None
    confirmed_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class AIScoreResultResponse(BaseSchema):
    """AI 评分结果详情响应"""
    id: int
    answer_record_id: int
    question_id: int
    question_content: str
    candidate_answer: Optional[str] = None
    ai_score: float
    max_score: float
    score_reason: str
    matched_points: Optional[list[str]] = None
    missing_points: Optional[list[str]] = None
    confidence: float
    needs_review: bool
    review_status: str
    confirmed_score: Optional[float] = None
    hr_remark: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: str
    created_at: str


class ConfirmAIScoringRequest(BaseSchema):
    """HR 确认 AI 评分请求"""
    answer_record_id: int = Field(..., description="答题记录 ID")
    confirmed_score: float = Field(
        ..., ge=0, description="HR 确认的最终分数"
    )
    hr_remark: Optional[str] = Field(
        default=None, description="HR 备注"
    )


class RejectAIScoringRequest(BaseSchema):
    """HR 拒绝 AI 评分请求"""
    answer_record_id: int = Field(..., description="答题记录 ID")
    hr_remark: Optional[str] = Field(
        default=None, description="拒绝原因"
    )


class AIScoreListResponse(BaseSchema):
    """AI 评分记录列表响应"""
    items: list[AIScoreResultResponse] = []
    total: int
    page: int
    page_size: int


class AIScoringStatusResponse(BaseSchema):
    """AI 评分状态响应"""
    answer_record_id: int
    has_ai_score: bool
    review_status: Optional[str] = None
    ai_score: Optional[float] = None
    confirmed_score: Optional[float] = None
    message: str
