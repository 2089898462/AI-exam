"""
考试 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class ExamCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    exam_code: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    duration_minutes: int = Field(..., gt=0, le=1440)
    pass_score: float = Field(default=0, ge=0)


class ExamUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    exam_code: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    pass_score: Optional[float] = Field(None, ge=0)


class ExamResponse(BaseSchema):
    id: int
    exam_code: Optional[str] = None
    title: str
    position: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: int
    pass_score: float
    status: str
    created_by: int
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ExamListResponse(BaseSchema):
    id: int
    exam_code: Optional[str] = None
    title: str
    position: Optional[str] = None
    status: str
    duration_minutes: int
    pass_score: float
    question_count: int = 0
    participant_count: int = 0
    created_at: datetime


class ExamDetailResponse(ExamResponse):
    question_count: int = 0
    questions: list = []


class ExamPublishResponse(BaseSchema):
    id: int
    status: str
    published_at: Optional[datetime] = None


class ExamCloseResponse(BaseSchema):
    id: int
    status: str
    closed_at: Optional[datetime] = None
