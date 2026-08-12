"""
试卷模板 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class TemplateCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class TemplateUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class TemplateResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    question_count: int = 0
    created_at: datetime


class TemplateDetailResponse(TemplateResponse):
    question_count: int = 0
    questions: list = []


class TemplateQuestionCreate(BaseSchema):
    type: str = Field(
        ...,
        pattern="^(single_choice|multiple_choice|true_false|short_answer)$",
    )
    content: str = Field(..., min_length=1)
    question_no: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    options: Optional[list[dict]] = None
    answer: str = Field(..., min_length=1)
    score: float = Field(default=0, ge=0)
    sort_order: int = Field(default=0, ge=0)


class TemplateQuestionUpdate(BaseSchema):
    type: Optional[str] = Field(
        None,
        pattern="^(single_choice|multiple_choice|true_false|short_answer)$",
    )
    content: Optional[str] = Field(None, min_length=1)
    question_no: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    options: Optional[list[dict]] = None
    answer: Optional[str] = None
    score: Optional[float] = Field(None, ge=0)
    sort_order: Optional[int] = Field(None, ge=0)


class TemplateQuestionResponse(BaseSchema):
    id: int
    template_id: int
    question_no: Optional[str] = None
    category: Optional[str] = None
    type: str
    content: str
    options: Optional[list[dict]] = None
    answer: str
    score: float
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CreateExamFromTemplateRequest(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    exam_code: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    duration_minutes: int = Field(default=60, gt=0, le=1440)
    pass_score: float = Field(default=60, ge=0)


class ImportQuestionsToTemplateRequest(BaseSchema):
    questions: list[TemplateQuestionCreate]
