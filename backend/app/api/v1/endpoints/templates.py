"""
试卷模板管理端点
所有接口均需 Bearer Token 认证
HR / Admin 角色可访问
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.template import (
    CreateExamFromTemplateRequest,
    ImportQuestionsToTemplateRequest,
    TemplateCreate,
    TemplateDetailResponse,
    TemplateListResponse,
    TemplateQuestionCreate,
    TemplateQuestionResponse,
    TemplateQuestionUpdate,
    TemplateResponse,
    TemplateUpdate,
)
from app.services.template_service import TemplateService
from app.utils.response import ApiResponse

router = APIRouter()


# ==================== 模板 CRUD ====================

@router.post("", status_code=201)
async def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    template = service.create_template(
        name=data.name,
        description=data.description,
        created_by=current_user.id,
    )
    return ApiResponse.created(
        data=TemplateResponse.model_validate(template).model_dump()
    )


@router.get("")
async def list_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    items, total = service.list_templates(
        current_user=current_user,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    
    result_list = []
    for item in items:
        question_count = service.count_questions(item.id)
        item_data = TemplateListResponse.model_validate(item).model_dump()
        item_data["question_count"] = question_count
        result_list.append(item_data)
    
    return ApiResponse.paginated(
        items=result_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    template = service.get_template_detail(
        template_id=template_id,
        current_user=current_user,
    )
    question_count = service.count_questions(template_id)
    questions = service.get_template_questions(template_id)
    
    result = TemplateDetailResponse.model_validate(template)
    result.question_count = question_count
    result.questions = [
        TemplateQuestionResponse.model_validate(q).model_dump()
        for q in questions
    ]
    
    return ApiResponse.success(data=result.model_dump())


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    template = service.update_template(
        template_id=template_id,
        current_user=current_user,
        **data.model_dump(exclude_unset=True),
    )
    return ApiResponse.success(
        data=TemplateResponse.model_validate(template).model_dump()
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    service.delete_template(
        template_id=template_id,
        current_user=current_user,
    )
    return ApiResponse.success(message="删除成功")


@router.post("/{template_id}/activate")
async def activate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    template = service.activate_template(
        template_id=template_id,
        current_user=current_user,
    )
    return ApiResponse.success(
        data=TemplateResponse.model_validate(template).model_dump()
    )


@router.post("/{template_id}/deactivate")
async def deactivate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    template = service.deactivate_template(
        template_id=template_id,
        current_user=current_user,
    )
    return ApiResponse.success(
        data=TemplateResponse.model_validate(template).model_dump()
    )


# ==================== 模板题目管理 ====================

@router.get("/{template_id}/questions")
async def list_template_questions(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    questions = service.get_template_questions(template_id)
    result = [
        TemplateQuestionResponse.model_validate(q).model_dump()
        for q in questions
    ]
    return ApiResponse.success(data=result)


@router.post("/{template_id}/questions", status_code=201)
async def create_template_question(
    template_id: int,
    data: TemplateQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    question = service.create_template_question(
        template_id=template_id,
        current_user=current_user,
        **data.model_dump(),
    )
    return ApiResponse.created(
        data=TemplateQuestionResponse.model_validate(question).model_dump()
    )


@router.post("/{template_id}/questions/batch", status_code=201)
async def batch_create_questions(
    template_id: int,
    data: ImportQuestionsToTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    questions_data = [q.model_dump() for q in data.questions]
    questions = service.batch_create_questions(
        template_id=template_id,
        current_user=current_user,
        questions=questions_data,
    )
    result = [
        TemplateQuestionResponse.model_validate(q).model_dump()
        for q in questions
    ]
    return ApiResponse.created(data=result)


@router.put("/{template_id}/questions/{question_id}")
async def update_template_question(
    template_id: int,
    question_id: int,
    data: TemplateQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    question = service.update_template_question(
        template_id=template_id,
        question_id=question_id,
        current_user=current_user,
        **data.model_dump(exclude_unset=True),
    )
    return ApiResponse.success(
        data=TemplateQuestionResponse.model_validate(question).model_dump()
    )


@router.delete("/{template_id}/questions/{question_id}")
async def delete_template_question(
    template_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    service.delete_template_question(
        template_id=template_id,
        question_id=question_id,
        current_user=current_user,
    )
    return ApiResponse.success(message="删除成功")


@router.delete("/{template_id}/questions")
async def delete_all_template_questions(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    service.delete_all_questions(
        template_id=template_id,
        current_user=current_user,
    )
    return ApiResponse.success(message="清空成功")


@router.post("/{template_id}/questions/import")
async def import_questions_to_template(
    template_id: int,
    data: ImportQuestionsToTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    questions_data = [q.model_dump() for q in data.questions]
    result = service.import_questions_to_template(
        template_id=template_id,
        current_user=current_user,
        questions_data=questions_data,
    )
    return ApiResponse.success(data=result)


# ==================== 基于模板创建考试 ====================

@router.post("/{template_id}/create-exam")
async def create_exam_from_template(
    template_id: int,
    data: CreateExamFromTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = TemplateService(db)
    exam = service.create_exam_from_template(
        template_id=template_id,
        current_user=current_user,
        **data.model_dump(exclude_unset=True),
    )
    return ApiResponse.created(
        data={
            "exam_id": exam.id,
            "title": exam.title,
            "status": exam.status,
        }
    )
