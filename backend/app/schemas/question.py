"""
题目 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class QuestionCreate(BaseSchema):
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


class QuestionUpdate(BaseSchema):
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


class QuestionResponse(BaseSchema):
    id: int
    exam_id: int
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


class QuestionResponseWithoutAnswer(BaseSchema):
    id: int
    exam_id: int
    question_no: Optional[str] = None
    category: Optional[str] = None
    type: str
    content: str
    options: Optional[list[dict]] = None
    score: float
    sort_order: int
