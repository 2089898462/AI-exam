"""
知识库管理 API
岗位、评分模板、评分规则的 CRUD 管理
以及 RAG 检索接口
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_admin, require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.knowledge_base import (
    PositionCreate,
    PositionResponse,
    PositionUpdate,
    ScoringContextResponse,
    ScoringRuleCreate,
    ScoringRuleResponse,
    ScoringRuleUpdate,
    ScoringTemplateCreate,
    ScoringTemplateResponse,
    ScoringTemplateUpdate,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter(tags=["知识库管理"])


# ==================== 岗位管理 ====================

@router.post("/positions", response_model=PositionResponse, summary="创建岗位")
async def create_position(
    request: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """创建新岗位（仅管理员）"""
    service = KnowledgeBaseService(db)
    position = service.create_position(name=request.name, description=request.description)
    return position


@router.get("/positions", response_model=list[PositionResponse], summary="查询岗位列表")
async def list_positions(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询岗位列表（HR/管理员）"""
    service = KnowledgeBaseService(db)
    return service.list_positions(is_active=is_active)


@router.get("/positions/{position_id}", response_model=PositionResponse, summary="查询岗位详情")
async def get_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询岗位详情（HR/管理员）"""
    service = KnowledgeBaseService(db)
    position = service.get_position(position_id)
    if not position:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("岗位不存在")
    return position


@router.put("/positions/{position_id}", response_model=PositionResponse, summary="更新岗位")
async def update_position(
    position_id: int,
    request: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新岗位信息（仅管理员）"""
    service = KnowledgeBaseService(db)
    position = service.update_position(
        position_id=position_id,
        name=request.name,
        description=request.description,
        is_active=request.is_active,
    )
    return position


@router.delete("/positions/{position_id}", summary="删除岗位")
async def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """删除岗位（软删除，仅管理员）"""
    service = KnowledgeBaseService(db)
    service.delete_position(position_id)
    return {"message": "岗位已删除"}


# ==================== 评分模板管理 ====================

@router.post("/templates", response_model=ScoringTemplateResponse, summary="创建评分模板")
async def create_template(
    request: ScoringTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """创建评分模板（仅管理员）"""
    service = KnowledgeBaseService(db)
    template = service.create_template(
        position_id=request.position_id,
        name=request.name,
        description=request.description,
    )
    return template


@router.get("/templates", response_model=list[ScoringTemplateResponse], summary="查询模板列表")
async def list_templates(
    position_id: int | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询模板列表（HR/管理员）"""
    service = KnowledgeBaseService(db)
    return service.list_templates(position_id=position_id, is_active=is_active)


@router.get("/templates/{template_id}", response_model=ScoringTemplateResponse, summary="查询模板详情")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询模板详情（HR/管理员）"""
    service = KnowledgeBaseService(db)
    template = service.get_template(template_id)
    if not template:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("模板不存在")
    return template


@router.put("/templates/{template_id}", response_model=ScoringTemplateResponse, summary="更新模板")
async def update_template(
    template_id: int,
    request: ScoringTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新模板（仅管理员）"""
    service = KnowledgeBaseService(db)
    template = service.update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        is_active=request.is_active,
    )
    return template


# ==================== 评分规则管理 ====================

@router.post("/rules", response_model=ScoringRuleResponse, summary="创建评分规则")
async def create_rule(
    request: ScoringRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """创建评分规则（仅管理员）"""
    service = KnowledgeBaseService(db)
    rule = service.create_rule(
        template_id=request.template_id,
        rule_name=request.rule_name,
        content=request.content,
        rule_type=request.rule_type,
        key_points=request.key_points,
        deduction_rules=request.deduction_rules,
        weight=request.weight,
    )
    return rule


@router.get("/rules", response_model=list[ScoringRuleResponse], summary="查询规则列表")
async def list_rules(
    template_id: int | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询规则列表（HR/管理员）"""
    service = KnowledgeBaseService(db)
    return service.list_rules(template_id=template_id, is_active=is_active)


@router.get("/rules/{rule_id}", response_model=ScoringRuleResponse, summary="查询规则详情")
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询规则详情（HR/管理员）"""
    service = KnowledgeBaseService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("规则不存在")
    return rule


@router.put("/rules/{rule_id}", response_model=ScoringRuleResponse, summary="更新规则")
async def update_rule(
    rule_id: int,
    request: ScoringRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新规则（创建新版本，仅管理员）"""
    service = KnowledgeBaseService(db)
    rule = service.update_rule(
        rule_id=rule_id,
        rule_name=request.rule_name,
        content=request.content,
        key_points=request.key_points,
        deduction_rules=request.deduction_rules,
        weight=request.weight,
        is_active=request.is_active,
    )
    return rule


# ==================== RAG 检索 ====================

@router.get("/retrieve", response_model=ScoringContextResponse, summary="RAG 检索评分上下文")
async def retrieve_scoring_context(
    position_id: int | None = None,
    template_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """检索评分上下文（RAG），用于 AI 评分时注入评分标准"""
    service = KnowledgeBaseService(db)
    return service.retrieve_scoring_context(position_id=position_id, template_id=template_id)


@router.get("/templates/by-position/{position_id}", response_model=ScoringTemplateResponse | None, summary="根据岗位查找模板")
async def find_template_by_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """根据岗位查找激活的评分模板"""
    service = KnowledgeBaseService(db)
    return service.find_template_by_position(position_id)
