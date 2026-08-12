"""
知识库 API Schema
"""
from datetime import datetime

from pydantic import BaseModel


# ==================== 岗位 ====================

class PositionCreate(BaseModel):
    name: str
    description: str | None = None


class PositionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class PositionResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 评分模板 ====================

class ScoringTemplateCreate(BaseModel):
    position_id: int
    name: str
    description: str | None = None


class ScoringTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ScoringTemplateResponse(BaseModel):
    id: int
    position_id: int
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 评分规则 ====================

class ScoringRuleCreate(BaseModel):
    template_id: int
    rule_name: str
    content: str
    rule_type: str = "knowledge_point"
    key_points: str | None = None
    deduction_rules: str | None = None
    weight: float = 1.0


class ScoringRuleUpdate(BaseModel):
    rule_name: str | None = None
    content: str | None = None
    key_points: str | None = None
    deduction_rules: str | None = None
    weight: float | None = None
    is_active: bool | None = None


class ScoringRuleResponse(BaseModel):
    id: int
    template_id: int
    version: int
    rule_name: str
    rule_type: str
    content: str
    key_points: str | None = None
    deduction_rules: str | None = None
    weight: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== RAG 检索 ====================

class ScoringContextResponse(BaseModel):
    position: dict | None = None
    template: dict | None = None
    rules: list[dict] = []
    rule_versions: list[dict] = []
