"""
评分 API Schema
供 Backend 调用的 AI 评分接口请求/响应模型
"""
from typing import Optional

from pydantic import BaseModel, Field


class ScoringRequest(BaseModel):
    """评分请求"""
    question: str = Field(..., min_length=1, description="题目内容")
    standard_answer: str = Field(default="", description="标准答案")
    user_answer: str = Field(..., min_length=1, description="用户答案")
    max_score: float = Field(default=10.0, gt=0, description="满分")
    scoring_rules: Optional[str] = Field(default=None, description="评分规则")
    prompt_version: str = Field(default="v3", description="Prompt 版本: v1/v2/v3")


class ScoringResponse(BaseModel):
    """评分响应"""
    score: float = Field(description="得分")
    reason: str = Field(description="评分理由")
    matched_points: list[str] = Field(default_factory=list, description="匹配的知识点 (v2)")
    missing_points: list[str] = Field(default_factory=list, description="遗漏要点")
    confidence: float = Field(ge=0, le=1, description="置信度")
    prompt_version: str = Field(default="v3", description="实际使用的 Prompt 版本")
    needs_review: bool = Field(default=False, description="是否需要人工复核")
    score_level: str = Field(default="", description="评分等级 (v3): full_correct/partial_correct/incorrect")
    question_type: str = Field(default="", description="题型 (v3): short_answer/concept/analysis")
    keyword_coverage: Optional[float] = Field(default=None, description="知识点覆盖率 (v3, 0-1)")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: str = ""
