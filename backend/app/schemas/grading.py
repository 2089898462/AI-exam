"""
评分 API Schema
评分记录和评分规则的请求/响应数据模型
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


# ============================================================
# 评分记录
# ============================================================
class GradingRecordCreate(BaseSchema):
    """创建评分记录请求"""
    exam_record_id: int = Field(..., description="考试记录 ID")
    grading_type: str = Field(
        default="auto",
        description="评分类型: auto(自动) / ai(AI) / hybrid(混合)",
    )


class GradingRecordResponse(BaseSchema):
    """评分记录响应"""
    id: int
    exam_record_id: int
    status: str
    grading_type: str
    total_score: Optional[float] = None
    auto_score: Optional[float] = None
    ai_score: Optional[float] = None
    passed: Optional[bool] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GradingStatusResponse(BaseSchema):
    """评分状态响应（用于状态查询API）"""
    exists: bool
    id: Optional[int] = None
    exam_record_id: Optional[int] = None
    status: str
    grading_type: Optional[str] = None
    total_score: Optional[float] = None
    auto_score: Optional[float] = None
    ai_score: Optional[float] = None
    passed: Optional[bool] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    message: Optional[str] = None


class GradingCompleteRequest(BaseSchema):
    """完成评分请求"""
    total_score: float = Field(..., description="最终总分")
    auto_score: Optional[float] = Field(default=None, description="客观题得分")
    ai_score: Optional[float] = Field(default=None, description="AI评分得分")
    passed: Optional[bool] = Field(default=None, description="是否及格")


# ============================================================
# 评分规则
# ============================================================
class ScoreRuleCreate(BaseSchema):
    """创建评分规则请求"""
    exam_id: int = Field(..., description="考试 ID")
    question_type: str = Field(
        ...,
        description="题型: single_choice / multiple_choice / true_false / short_answer",
    )
    score_method: str = Field(
        default="auto_compare",
        description="评分方法: auto_compare(自动比对) / ai_score(AI评分) / manual(手动)",
    )
    pass_score: float = Field(default=0, description="该题型及格分")
    weight: float = Field(default=1.0, description="权重")
    is_enabled: bool = Field(default=True, description="是否启用")


class ScoreRuleUpdate(BaseSchema):
    """更新评分规则请求"""
    score_method: Optional[str] = Field(default=None)
    pass_score: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    is_enabled: Optional[bool] = Field(default=None)


class ScoreRuleResponse(BaseSchema):
    """评分规则响应"""
    id: int
    exam_id: int
    question_type: str
    score_method: str
    pass_score: float
    weight: float
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


# ============================================================
# 评分结果查询
# ============================================================
class GradingResultItem(BaseSchema):
    """评分结果列表项"""
    id: int
    exam_record_id: int
    exam_id: int
    candidate_name: str
    candidate_phone: Optional[str] = None
    status: str
    grading_type: str
    total_score: Optional[float] = None
    auto_score: Optional[float] = None
    ai_score: Optional[float] = None
    passed: Optional[bool] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


class GradingResultListResponse(BaseSchema):
    """评分结果列表响应"""
    items: list[GradingResultItem] = []
    total: int
    page: int
    page_size: int


class AnswerDetailResponse(BaseSchema):
    """答题详情响应"""
    answer_id: int
    question_id: int
    question_type: str
    question_content: str
    question_no: Optional[str] = None
    candidate_answer: Optional[str] = None
    standard_answer: Optional[str] = None
    score: Optional[float] = None
    full_score: float
    is_correct: Optional[bool] = None
    options: Optional[list] = None


class GradingStatisticsResponse(BaseSchema):
    """评分统计信息"""
    total_questions: int
    answered_count: int
    correct_count: int
    correct_rate: float


class GradingResultDetailResponse(BaseSchema):
    """评分结果详情响应"""
    grading_id: int
    status: str
    grading_type: str
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
    start_time: Optional[str] = None
    complete_time: Optional[str] = None
    error_message: Optional[str] = None
    statistics: GradingStatisticsResponse
    answers: list[AnswerDetailResponse] = []
