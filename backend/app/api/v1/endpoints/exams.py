"""
考试管理端点
所有接口均需 Bearer Token 认证
HR / Admin 角色可访问
"""
import json

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.permissions import require_authenticated, require_hr_or_admin
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
from app.schemas.exam_statistics import (
    ExamAnalysisResponse,
    ExamResultsResponse,
    ExamStatisticsListResponse,
    ExamStatisticsResponse,
    RecordAnswersResponse,
)
from app.schemas.question import QuestionResponse
from app.services.exam_import_service import ExamImportService
from app.services.exam_service import ExamService
from app.services.exam_statistics_service import ExamStatisticsService
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


@router.get("/entry/by-code")
async def get_exam_by_code(
    exam_code: str = Query(..., description="考试访问码"),
    db: Session = Depends(get_db),
):
    """通过考试码查询考试信息（候选人入口，无需认证）"""
    from app.exceptions import NotFoundException, ValidationException
    service = ExamService(db)
    exam = service.get_by_code(exam_code=exam_code)
    if not exam:
        raise NotFoundException(f"考试码 {exam_code} 无效")
    if exam.status != "published":
        raise ValidationException("该考试尚未发布，无法参加")
    question_count = service.count_questions(exam.id)
    return ApiResponse.success(data={
        "id": exam.id,
        "title": exam.title,
        "description": exam.description or "",
        "duration_minutes": exam.duration_minutes,
        "pass_score": exam.pass_score,
        "question_count": question_count,
        "status": exam.status,
        "exam_code": exam.exam_code,
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


@router.post("/{exam_id}/clone")
async def clone_exam(
    exam_id: int,
    new_title: str | None = Query(default=None, description="新考试标题，默认在原标题后加（副本）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """复制考试为新实例（用于试卷复用）

    只有已关闭的考试才能复制，生成的新考试为草稿状态，
    包含原考试的所有题目，但不包含考试记录和答题数据。
    """
    service = ExamService(db)
    exam = service.clone_exam(
        exam_id=exam_id,
        current_user=current_user,
        new_title=new_title,
    )
    return ApiResponse.success(data=ExamResponse.model_validate(exam).model_dump())


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
        # 使用 utf-8-sig 处理带 BOM 的文件
        json_text = content.decode("utf-8-sig")
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


# ============================================================
# 考试统计接口（S4.4-A 新增）
# ============================================================

@router.get("/statistics")
async def get_exams_statistics_list(
    status: str | None = Query(default=None, description="考试状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取考试统计列表（HR/Admin）

    返回多个考试的统计数据，支持状态筛选和分页
    """
    service = ExamStatisticsService(db)
    result = service.get_exams_statistics_list(
        current_user=current_user,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result)


@router.get("/{exam_id}/statistics")
async def get_exam_statistics(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取单个考试的统计数据（HR/Admin）

    返回考试的完整统计信息，包括：
    - 参与人数、已完成人数、未完成人数
    - 平均成绩、最高成绩、最低成绩
    - 通过人数、通过率
    """
    service = ExamStatisticsService(db)
    result = service.get_exam_statistics(
        exam_id=exam_id,
        current_user=current_user,
    )
    return ApiResponse.success(data=result)


# ============================================================
# S4.4-B 数据查询接口
# ============================================================

@router.get("/{exam_id}/analysis")
async def get_exam_analysis(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取考试完整分析数据（HR/Admin）

    返回：
    - 基础信息（名称、状态、创建时间、发布时间）
    - 统计信息（参与人数、平均分、通过率等）
    - 答题概况（总题数、总分、平均得分率）
    """
    service = ExamStatisticsService(db)
    result = service.get_exam_analysis(
        exam_id=exam_id,
        current_user=current_user,
    )
    return ApiResponse.success(data=result)


@router.get("/{exam_id}/results")
async def get_exam_results(
    exam_id: int,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取考试成绩列表（HR/Admin，分页）

    返回每个参与人员的成绩信息：
    - 候选人标识、考试状态、提交时间、成绩、是否通过
    """
    service = ExamStatisticsService(db)
    result = service.get_exam_results(
        exam_id=exam_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result)


@router.get("/{exam_id}/records/{record_id}/answers")
async def get_record_answers(
    exam_id: int,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """获取考试答题详情（登录用户）

    权限规则：
    - Admin: 可查看所有答题详情
    - HR: 只能查看自己管理范围内的答题详情
    - Employee/Candidate: 只能查看自己的答题详情

    返回每道题的：
    - 题目内容、用户答案、标准答案、得分、评分状态
    """
    service = ExamStatisticsService(db)
    result = service.get_record_answers(
        exam_id=exam_id,
        record_id=record_id,
        current_user=current_user,
    )
    return ApiResponse.success(data=result)
