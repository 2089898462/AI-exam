"""
考试记录 & 答题记录 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 答题记录
# ============================================================
class AnswerSubmit(BaseModel):
    """提交答案请求"""
    question_id: int
    answer_content: Optional[str] = None


class AnswerResponse(BaseModel):
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
class ExamRecordCreate(BaseModel):
    """创建考试记录（候选人进入考试）"""
    exam_id: int
    candidate_name: str = Field(..., min_length=1, max_length=64)
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None


class ExamRecordSubmit(BaseModel):
    """提交考试请求"""
    answers: list[AnswerSubmit]


class ExamRecordResponse(BaseModel):
    """考试记录响应"""
    id: int
    exam_id: int
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    status: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    score: Optional[float] = None
    answers: list[AnswerResponse] = []


class ExamRecordListResponse(BaseModel):
    """考试记录列表响应"""
    id: int
    exam_id: int
    candidate_name: str
    status: str
    score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime


# ============================================================
# AI 报告
# ============================================================
class AiReportResponse(BaseModel):
    """AI 报告响应"""
    strengths: dict
    weaknesses: dict
    learning_suggestions: dict
    raw_report: Optional[str] = None
    created_at: datetime
