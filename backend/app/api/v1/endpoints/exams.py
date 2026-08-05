"""
考试管理端点
所有接口均需 Bearer Token 认证
HR / Admin 角色可访问
"""
import json

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.exceptions import ValidationException
from app.models.user import User
from app.schemas.exam import (
    ExamCloseResponse,
    ExamCreate,
    ExamDetailResponse,
    ExamListResponse,
    ExamPublishResponse,
    ExamResponse,
    ExamUpdate,
)
from app.schemas.question import QuestionResponse
from app.services.exam_import_service import ExamImportService
from app.services.exam_service import ExamService
from app.services.question_service import QuestionService
from app.utils.response import ApiResponse

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("", status_code=201)
async def create_exam(
    data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    exam = service.create_exam(
        title=data.title,
        exam_code=data.exam_code,
        position=data.position,
        description=data.description,
        duration_minutes=data.duration_minutes,
        pass_score=data.pass_score,
        created_by=current_user.id,
    )
    return ApiResponse.created(data=ExamResponse.model_validate(exam).model_dump())


@router.get("")
async def list_exams(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    items, total = service.list_exams(
        current_user=current_user,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    exam_list = [ExamListResponse.model_validate(item) for item in items]
    return ApiResponse.paginated(
        items=[e.model_dump() for e in exam_list],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{exam_id}/info")
async def get_exam_public_info(
    exam_id: int,
    db: Session = Depends(get_db),
):
    """公开考试信息（候选人查看，无需认证）"""
    service = ExamService(db)
    exam = service.get(exam_id)
    if not exam:
        from app.exceptions import NotFoundException
        raise NotFoundException(f"考试 {exam_id} 不存在")
    question_count = service.count_questions(exam_id)
    return ApiResponse.success(data={
        "id": exam.id,
        "title": exam.title,
        "description": exam.description or "",
        "duration_minutes": exam.duration_minutes,
        "pass_score": exam.pass_score,
        "question_count": question_count,
        "status": exam.status,
    })


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    exam = service.get_exam_detail(exam_id)
    question_count = service.count_questions(exam_id)
    question_service = QuestionService(db)
    questions = question_service.get_by_exam(exam_id)
    result = ExamDetailResponse.model_validate(exam)
    result.question_count = question_count
    result.questions = [QuestionResponse.model_validate(q).model_dump() for q in questions]
    return ApiResponse.success(data=result.model_dump())


@router.put("/{exam_id}")
async def update_exam(
    exam_id: int,
    data: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    exam = service.update_exam(
        exam_id=exam_id,
        current_user=current_user,
        **data.model_dump(exclude_unset=True),
    )
    return ApiResponse.success(data=ExamResponse.model_validate(exam).model_dump())


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    service.delete_exam(exam_id=exam_id, current_user=current_user)
    return ApiResponse.success(message="删除成功")


@router.post("/{exam_id}/publish")
async def publish_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    exam = service.publish_exam(exam_id=exam_id, current_user=current_user)
    return ApiResponse.success(data=ExamPublishResponse.model_validate(exam).model_dump())


@router.post("/{exam_id}/close")
async def close_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = ExamService(db)
    exam = service.close_exam(exam_id=exam_id, current_user=current_user)
    return ApiResponse.success(data=ExamCloseResponse.model_validate(exam).model_dump())


@router.get("/{exam_id}/questions")
async def list_exam_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    service = QuestionService(db)
    questions = service.get_by_exam(exam_id)
    result = [QuestionResponse.model_validate(q).model_dump() for q in questions]
    return ApiResponse.success(data=result)


@router.post("/{exam_id}/import")
async def import_exam(
    exam_id: int,
    file: UploadFile = File(..., description="JSON 考试文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    if not file.filename or not file.filename.endswith(".json"):
        raise ValidationException("仅支持 .json 格式文件")

    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise ValidationException(
            f"文件大小超过限制，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    try:
        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise ValidationException(
                f"文件大小超过限制，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        json_text = content.decode("utf-8")
        json_data = json.loads(json_text)
    except UnicodeDecodeError:
        raise ValidationException("文件编码错误，请使用 UTF-8 编码")
    except json.JSONDecodeError as e:
        raise ValidationException(f"JSON 格式错误: {str(e)}")

    service = ExamImportService(db)
    result = service.import_exam(
        exam_id=exam_id,
        current_user=current_user,
        json_data=json_data,
    )
    return ApiResponse.success(data=result)
