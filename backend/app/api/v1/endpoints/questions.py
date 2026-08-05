"""
题目管理端点
所有接口均需 Bearer Token 认证
HR / Admin 角色可访问
"""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services.question_service import QuestionService
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("", status_code=201)
async def create_question(
    exam_id: int = Query(..., description="考试 ID"),
    data: QuestionCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = QuestionService(db)
    question = service.create_question(
        exam_id=exam_id,
        current_user=current_user,
        **data.model_dump(exclude_unset=True),
    )
    return ApiResponse.created(data=QuestionResponse.model_validate(question).model_dump())


@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    exam_id: int = Query(..., description="考试 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = QuestionService(db)
    service.delete_question(
        exam_id=exam_id,
        question_id=question_id,
        current_user=current_user,
    )
    return ApiResponse.success(message="删除成功")
