"""
考试统计 Schema
"""
from typing import Optional

from pydantic import BaseModel, Field


class ExamStatisticsResponse(BaseModel):
    """考试统计响应"""
    exam_id: int
    exam_title: str
    exam_status: str
    pass_score: float
    total_participants: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    average_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None
    pass_count: int = 0
    pass_rate: Optional[float] = None


class ExamStatisticsListResponse(BaseModel):
    """考试统计列表响应"""
    items: list[ExamStatisticsResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class CandidateHistoryItem(BaseModel):
    """候选人历史考试项"""
    exam_record_id: int
    exam_id: int
    exam_title: str
    exam_position: Optional[str] = None
    exam_status: str
    record_status: str
    submitted_at: Optional[str] = None
    score: Optional[float] = None
    passed: Optional[bool] = None
    pass_score: float


class CandidateHistoryResponse(BaseModel):
    """候选人历史考试响应"""
    candidate_id: int
    candidate_name: Optional[str] = None
    total_exams: int = 0
    completed_exams: int = 0
    passed_exams: int = 0
    failed_exams: int = 0
    history: list[CandidateHistoryItem] = []


class CandidateHistoryByPhoneResponse(BaseModel):
    """通过手机号查询候选人历史响应"""
    phone: str
    candidate_name: Optional[str] = None
    total_exams: int = 0
    completed_exams: int = 0
    passed_exams: int = 0
    failed_exams: int = 0
    history: list[CandidateHistoryItem] = []


# ============================================================
# S4.4-B 数据查询接口 Schema
# ============================================================

class ExamAnalysisResponse(BaseModel):
    """考试分析响应"""
    exam_id: int
    exam_title: str
    exam_status: str
    exam_position: Optional[str] = None
    created_at: Optional[str] = None
    published_at: Optional[str] = None
    duration_minutes: int
    pass_score: float
    statistics: dict = {}
    answer_overview: dict = {}


class ExamResultItem(BaseModel):
    """考试成绩列表项"""
    record_id: int
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    status: str
    submitted_at: Optional[str] = None
    started_at: Optional[str] = None
    score: Optional[float] = None
    passed: Optional[bool] = None


class ExamResultsResponse(BaseModel):
    """考试成绩列表响应"""
    exam_id: int
    items: list[ExamResultItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class CandidateHistoryPaginatedResponse(BaseModel):
    """候选人历史考试分页响应"""
    candidate_id: int
    candidate_name: Optional[str] = None
    total: int = 0
    page: int = 1
    page_size: int = 20
    history: list[CandidateHistoryItem] = []


class AnswerDetailItem(BaseModel):
    """答题详情项"""
    answer_id: int
    question_id: int
    question_content: str
    question_type: str
    question_score: float
    user_answer: Optional[str] = None
    standard_answer: Optional[str] = None
    score: Optional[float] = None
    is_correct: Optional[bool] = None
    grading_status: str
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None


class RecordAnswersResponse(BaseModel):
    """考试答题详情响应"""
    exam_id: int
    record_id: int
    candidate_name: str
    exam_status: str
    total_questions: int = 0
    completed_questions: int = 0
    total_score: float = 0
    earned_score: float = 0
    answers: list[AnswerDetailItem] = []
