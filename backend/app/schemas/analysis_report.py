"""
候选人分析报告 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalysisReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_record_id: int
    participant_id: Optional[int] = None
    candidate_user_id: Optional[int] = None
    overall_score: float
    analysis_summary: str
    knowledge_mastery: Optional[str] = None
    strengths: Optional[str] = None
    weak_points: Optional[str] = None
    interview_focus: Optional[str] = None
    suggested_questions: Optional[str] = None
    model_name: Optional[str] = None
    analysis_version: str = "v1"
    status: str = "pending"
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    hr_remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AnalysisReportListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_record_id: int
    participant_id: Optional[int] = None
    candidate_user_id: Optional[int] = None
    overall_score: float
    analysis_summary: str
    status: str
    analysis_version: str
    created_at: datetime


class AnalysisReviewRequest(BaseModel):
    hr_remark: str = Field(
        ..., min_length=1, max_length=1000, description="HR 审核备注"
    )
