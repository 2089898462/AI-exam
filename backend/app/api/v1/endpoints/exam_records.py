"""
考试记录端点
候选人考试流程 API
候选人端点无需认证（候选人非系统用户）
HR 管理端点需 JWT + 角色校验
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.exam_record import (
    AnswerBatchCreate,
    AnswerCreate,
    AnswerResponse,
    ExamPaperResponse,
    ExamRecordCreate,
    ExamRecordDetailResponse,
    ExamRecordListResponse,
    ExamRecordResponse,
    PaperQuestionResponse,
)
from app.services.answer_record_service import AnswerRecordService
from app.services.exam_record_service import ExamRecordService
from app.services.exam_service import ExamService
from app.services.question_service import QuestionService
from app.utils.response import ApiResponse

router = APIRouter()
hr_router = APIRouter()


# ============================================================
# 候选人端点（无需认证）
# ============================================================

@router.post("", status_code=201)
async def create_exam_record(
    data: ExamRecordCreate,
    db: Session = Depends(get_db),
):
    """创建候选人考试记录（候选人进入考试）"""
    service = ExamRecordService(db)
    record = service.create_exam_record(
        exam_id=data.exam_id,
        candidate_name=data.candidate_name,
        candidate_phone=data.candidate_phone,
        candidate_email=data.candidate_email,
    )
    return ApiResponse.created(
        data=ExamRecordResponse.model_validate(record).model_dump()
    )


@router.get("/{record_id}")
async def get_exam_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取考试记录详情"""
    service = ExamRecordService(db)
    record = service.get_record_by_id(record_id)
    return ApiResponse.success(
        data=ExamRecordResponse.model_validate(record).model_dump()
    )


@router.get("/{record_id}/paper")
async def get_exam_paper(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取考试试卷（候选人答题页面，无需认证）"""
    record_service = ExamRecordService(db)
    record = record_service.get_record_by_id(record_id)

    exam_service = ExamService(db)
    exam = exam_service.get(record.exam_id)
    if not exam:
        from app.exceptions import NotFoundException
        raise NotFoundException(f"考试 {record.exam_id} 不存在")

    question_service = QuestionService(db)
    questions = question_service.get_by_exam(record.exam_id)
    question_count = len(questions)

    paper_questions = [
        PaperQuestionResponse(
            id=q.id,
            exam_id=q.exam_id,
            question_no=q.question_no,
            category=q.category,
            type=q.type,
            content=q.content,
            options=q.options,
            score=q.score,
            sort_order=q.sort_order,
        ).model_dump()
        for q in questions
    ]

    data = ExamPaperResponse(
        exam_id=exam.id,
        exam_title=exam.title,
        exam_description=exam.description or None,
        duration_minutes=exam.duration_minutes,
        pass_score=exam.pass_score,
        question_count=question_count,
        questions=paper_questions,
        record_id=record.id,
        candidate_name=record.candidate_name,
        status=record.status,
    )
    return ApiResponse.success(data=data.model_dump())


@router.post("/{record_id}/start")
async def start_exam(
    record_id: int,
    db: Session = Depends(get_db),
):
    """开始考试（状态：not_started → in_progress）"""
    service = ExamRecordService(db)
    record = service.start_exam(record_id)
    return ApiResponse.success(
        data=ExamRecordResponse.model_validate(record).model_dump()
    )


@router.post("/{record_id}/answers")
async def save_answer(
    record_id: int,
    data: AnswerCreate,
    db: Session = Depends(get_db),
):
    """保存单题答案"""
    service = AnswerRecordService(db)
    answer = service.save_answer(
        record_id=record_id,
        question_id=data.question_id,
        answer_content=data.answer_content,
    )
    return ApiResponse.success(
        data=AnswerResponse.model_validate(answer).model_dump()
    )


@router.post("/{record_id}/answers/batch")
async def save_answers_batch(
    record_id: int,
    data: AnswerBatchCreate,
    db: Session = Depends(get_db),
):
    """批量保存答案"""
    service = AnswerRecordService(db)
    answers_raw = [a.model_dump() for a in data.answers]
    answers = service.save_answers_batch(record_id=record_id, answers=answers_raw)
    result = [AnswerResponse.model_validate(a).model_dump() for a in answers]
    return ApiResponse.success(data=result)


@router.get("/{record_id}/answers")
async def get_exam_answers(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取考试记录的历史答案（用于刷新恢复/断点续考）"""
    service = AnswerRecordService(db)
    answers = service.get_answers_by_record(record_id)
    result = [AnswerResponse.model_validate(a).model_dump() for a in answers]
    return ApiResponse.success(data=result)


@router.post("/{record_id}/submit")
async def submit_exam(
    record_id: int,
    db: Session = Depends(get_db),
):
    """提交考试（状态：in_progress → submitted）"""
    service = ExamRecordService(db)
    record = service.submit_exam(record_id)
    return ApiResponse.success(
        data=ExamRecordResponse.model_validate(record).model_dump()
    )


# ============================================================
# HR 管理端点（需 JWT + HR/Admin 权限）
# ============================================================

@hr_router.get("/{exam_id}/records")
async def list_exam_records(
    exam_id: int,
    status: str | None = Query(default=None, description="状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查看某考试的候选人考试记录（HR/Admin）"""
    service = ExamRecordService(db)
    records = service.list_exam_records(exam_id=exam_id, status=status)
    result = [ExamRecordListResponse.model_validate(r).model_dump() for r in records]
    return ApiResponse.success(data=result)
