"""
AI 评分请求/响应 Schema
"""
from pydantic import BaseModel, Field


class AIScoringRequest(BaseModel):
    """AI 评分请求"""
    question: str = Field(..., min_length=1, description="题目内容")
    standard_answer: str = Field(default="", description="标准答案")
    user_answer: str = Field(..., min_length=1, description="用户答案")
    max_score: float = Field(default=10.0, gt=0, description="满分")
    scoring_rules: str | None = Field(default=None, description="评分规则")


class AIScoringResponse(BaseModel):
    """AI 评分响应"""
    score: float = Field(description="得分 (0 ~ max_score)")
    reason: str = Field(description="评分理由")
    missing_points: list[str] = Field(default_factory=list, description="遗漏要点")
    confidence: float = Field(ge=0, le=1, description="置信度 (0-1)")
