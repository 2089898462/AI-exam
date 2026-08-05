"""
考试记录 API Schema
候选人考试流程的请求/响应数据模型
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


# ============================================================
# 答题记录
# ============================================================
class AnswerCreate(BaseSchema):
    """单题答题请求"""
    question_id: int = Field(..., description="题目 ID")
    answer_content: Optional[str] = Field(default=None, description="答案内容")


class AnswerBatchCreate(BaseSchema):
    """批量答题请求"""
    answers: list[AnswerCreate] = Field(..., min_length=1, description="答案列表")


class AnswerResponse(BaseSchema):
    """答题记录响应"""
    id: int
    exam_record_id: int
    question_id: int
    answer_content: Optional[str] = None
    score: Optional[float] = None
    is_correct: Optional[bool] = None
    ai_comment: Optional[str] = None


# ============================================================
# 考试记录
# ============================================================
class ExamRecordCreate(BaseSchema):
    """创建考试记录（候选人进入考试）"""
    exam_id: int = Field(..., description="考试 ID")
    candidate_name: str = Field(..., min_length=1, max_length=64, description="候选人姓名")
    candidate_phone: Optional[str] = Field(default=None, description="候选人手机")
    candidate_email: Optional[str] = Field(default=None, description="候选人邮箱")


class ExamRecordResponse(BaseSchema):
    """考试记录响应（基本信息）"""
    id: int
    exam_id: int
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    status: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    score: Optional[float] = None


class ExamRecordDetailResponse(ExamRecordResponse):
    """考试记录详情响应（含答题列表）"""
    answers: list[AnswerResponse] = []


class ExamRecordListResponse(BaseSchema):
    """考试记录列表响应"""
    id: int
    exam_id: int
    candidate_name: str
    status: str
    score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime


# ============================================================
# 候选人试卷（公开，不含答案）
# ============================================================
class PaperQuestionResponse(BaseSchema):
    """题目响应（候选人可见，不含正确答案）"""
    id: int
    exam_id: int
    question_no: Optional[str] = None
    category: Optional[str] = None
    type: str
    content: str
    options: Optional[list[dict]] = None
    score: float
    sort_order: int


class ExamPaperResponse(BaseSchema):
    """考试试卷响应（候选人进入考试时获取）"""
    exam_id: int
    exam_title: str
    exam_description: Optional[str] = None
    duration_minutes: Optional[int] = None
    pass_score: Optional[float] = None
    question_count: int
    questions: list[PaperQuestionResponse] = []
    record_id: int
    candidate_name: str
    status: str
