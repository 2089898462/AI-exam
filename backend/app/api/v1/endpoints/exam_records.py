"""
考试记录端点
候选人考试流程 API
候选人端点无需认证（候选人非系统用户）
HR 管理端点需 JWT + 角色校验
评分相关端点
"""
import threading
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.permissions import require_hr_or_admin
from app.db.session import _get_session_factory, get_db
from app.exceptions import NotFoundException
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
from app.schemas.grading import (
    GradingRecordCreate,
    GradingRecordResponse,
    GradingStatusResponse,
    ScoreRuleCreate,
    ScoreRuleResponse,
    ScoreRuleUpdate,
)
from app.services.answer_record_service import AnswerRecordService
from app.services.exam_record_service import ExamRecordService
from app.services.exam_service import ExamService
from app.services.grading_service import GradingService
from app.services.question_service import QuestionService
from app.services.score_rule_service import ScoreRuleService
from app.utils.response import ApiResponse

logger = get_logger(__name__)


def _trigger_auto_grade(record_id: int):
    """后台触发自动评分（不阻塞主请求）

    评分流程：
    1. 创建新 DB Session
    2. 调用 GradingService.auto_grade_exam
    3. 异常时记录日志，不影响已提交的考试结果

    Args:
        record_id: 考试记录 ID
    """
    def _run():
        session_factory = _get_session_factory()
        db = session_factory()
        try:
            grading_service = GradingService(db)
            grading_service.auto_grade_exam(record_id)
            logger.info(f"后台自动评分完成: record_id={record_id}")
        except Exception as e:
            logger.error(f"后台自动评分失败: record_id={record_id}, error={e}")
        finally:
            db.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

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
    """创建候选人考试记录（候选人进入考试）
    
    安全校验:
    1. 考试状态校验（必须 published）
    2. 考试凭证校验（如果设置了）
    3. 参与资格校验（必须在 ExamParticipant 列表中）
    4. 防重复提交校验
    """
    service = ExamRecordService(db)
    record = service.create_exam_record(
        exam_id=data.exam_id,
        candidate_name=data.candidate_name,
        candidate_phone=data.candidate_phone,
        candidate_email=data.candidate_email,
        exam_code=data.exam_code,
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
        # S8.4.4: 返回考试开始时间与服务器当前时间，供前端校准倒计时
        started_at=record.started_at,
        server_time=datetime.now(),
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
    data: dict = Body(default=None),
    db: Session = Depends(get_db),
):
    """提交考试（状态：in_progress → submitted）
    
    提交流程：
    1. 幂等检查：已提交直接返回当前状态
    2. 状态校验：not_started 禁止提交
    3. 更新状态为 submitted
    4. 记录提交时间
    5. 保存监考数据（如果有）
    6. 后台异步触发自动评分（不阻塞响应）
    
    监考数据格式（可选）：
    {
        "monitor_data": {
            "leave_count": 0,
            "total_hidden_duration": 0,
            "events": []
        }
    }
    
    AI评分在后台线程中执行：
    - 客观题自动评分（单选/多选/判断）
    - 主观题 AI 评分（简答题，调用 AI-Service）
    - 评分结果保存到数据库
    - 评分失败不影响提交结果
    """
    service = ExamRecordService(db)
    monitor_data = data.get("monitor_data") if data else None
    record = service.submit_exam(record_id, monitor_data=monitor_data)
    
    # 提交成功后，后台触发自动评分
    if record.status == "submitted":
        _trigger_auto_grade(record_id)
        logger.info(f"已触发后台自动评分: record_id={record_id}")
    
    return ApiResponse.success(
        data=ExamRecordResponse.model_validate(record).model_dump()
    )


@router.get("/{record_id}/grading")
async def get_grading_status(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取评分状态（候选人查看评分进度）
    
    返回评分记录状态：
    - 不存在时返回 { exists: false, status: "not_started" }
    - 存在时返回完整评分信息
    """
    # 验证考试记录存在
    record_service = ExamRecordService(db)
    record_service.get_record_by_id(record_id)
    
    grading_service = GradingService(db)
    status_data = grading_service.get_grading_status(record_id)
    return ApiResponse.success(data=status_data)


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


# ============================================================
# HR 评分管理端点（需 JWT + HR/Admin 权限）
# ============================================================

@hr_router.post("/records/{record_id}/grading", status_code=201)
async def create_grading_record(
    record_id: int,
    data: GradingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """创建评分记录（HR/Admin）"""
    service = GradingService(db)
    grading = service.create_grading_record(
        exam_record_id=record_id,
        grading_type=data.grading_type,
    )
    return ApiResponse.created(
        data=GradingRecordResponse.model_validate(grading).model_dump()
    )


@hr_router.get("/records/{record_id}/grading")
async def get_grading_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取评分记录详情（HR/Admin）"""
    service = GradingService(db)
    grading = service.get_grading_by_record_id(record_id)
    if not grading:
        raise NotFoundException("评分记录不存在")
    return ApiResponse.success(
        data=GradingRecordResponse.model_validate(grading).model_dump()
    )


@hr_router.post("/records/{record_id}/grading/start")
async def start_grading(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """开始评分（HR/Admin）"""
    service = GradingService(db)
    grading = service.get_grading_by_record_id(record_id)
    if not grading:
        raise NotFoundException("评分记录不存在")
    grading = service.start_grading(grading.id)
    return ApiResponse.success(
        data=GradingRecordResponse.model_validate(grading).model_dump()
    )


@hr_router.post("/records/{record_id}/grading/complete")
async def complete_grading(
    record_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """完成评分（HR/Admin）
    
    请求体：
    - total_score: 最终总分
    - auto_score: 客观题得分（可选）
    - ai_score: AI评分得分（可选）
    - passed: 是否及格（可选）
    """
    service = GradingService(db)
    grading = service.get_grading_by_record_id(record_id)
    if not grading:
        raise NotFoundException("评分记录不存在")
    grading = service.complete_grading(
        grading_id=grading.id,
        total_score=data.get("total_score", 0),
        auto_score=data.get("auto_score"),
        ai_score=data.get("ai_score"),
        passed=data.get("passed"),
    )
    return ApiResponse.success(
        data=GradingRecordResponse.model_validate(grading).model_dump()
    )


# ============================================================
# HR 评分规则管理端点
# ============================================================

@hr_router.post("/{exam_id}/score-rules", status_code=201)
async def create_score_rule(
    exam_id: int,
    data: ScoreRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """创建评分规则（HR/Admin）"""
    service = ScoreRuleService(db)
    rule = service.create_rule(
        exam_id=exam_id,
        question_type=data.question_type,
        score_method=data.score_method,
        pass_score=data.pass_score,
        weight=data.weight,
        is_enabled=data.is_enabled,
    )
    return ApiResponse.created(
        data=ScoreRuleResponse.model_validate(rule).model_dump()
    )


@hr_router.get("/{exam_id}/score-rules")
async def list_score_rules(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取考试的所有评分规则（HR/Admin）"""
    service = ScoreRuleService(db)
    rules = service.get_rules_by_exam(exam_id)
    result = [ScoreRuleResponse.model_validate(r).model_dump() for r in rules]
    return ApiResponse.success(data=result)


@hr_router.put("/score-rules/{rule_id}")
async def update_score_rule(
    rule_id: int,
    data: ScoreRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """更新评分规则（HR/Admin）"""
    service = ScoreRuleService(db)
    rule = service.update_rule(
        rule_id=rule_id,
        score_method=data.score_method,
        pass_score=data.pass_score,
        weight=data.weight,
        is_enabled=data.is_enabled,
    )
    return ApiResponse.success(
        data=ScoreRuleResponse.model_validate(rule).model_dump()
    )


@hr_router.delete("/score-rules/{rule_id}")
async def delete_score_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """删除评分规则（HR/Admin）"""
    service = ScoreRuleService(db)
    service.delete_rule(rule_id)
    return ApiResponse.success(message="删除成功")


@hr_router.post("/{exam_id}/score-rules/init")
async def init_default_score_rules(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """初始化默认评分规则（HR/Admin）
    
    自动创建四种题型的默认规则：
    - 单选/多选/判断：auto_compare
    - 简答：ai_score
    """
    service = ScoreRuleService(db)
    rules = service.init_default_rules(exam_id)
    result = [ScoreRuleResponse.model_validate(r).model_dump() for r in rules]
    return ApiResponse.success(data=result)


@hr_router.post("/records/{record_id}/auto-grade")
async def auto_grade_exam(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """执行自动评分（HR/Admin）
    
    自动评分流程：
    1. 加载答案记录和题目信息
    2. 逐题比对标准答案
    3. 计算客观题得分
    4. 保存评分结果
    5. 更新考试记录状态为 graded
    
    仅限客观题（单选/多选/判断）自动评分
    """
    service = GradingService(db)
    grading = service.auto_grade_exam(record_id)
    return ApiResponse.success(
        data=GradingRecordResponse.model_validate(grading).model_dump()
    )
