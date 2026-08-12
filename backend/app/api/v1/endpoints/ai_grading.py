"""
AI 阅卷 API 端点
HR 后台管理 AI 评分建议的触发、查看和确认

权限要求：
- HR / Admin 角色：触发评分、查看结果、确认/拒绝
- 候选人：禁止访问
- 普通用户：禁止访问
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_grading import (
    AIScoreListResponse,
    AIScoreResultResponse,
    AIScoringStatusResponse,
    ConfirmAIScoringRequest,
    RejectAIScoringRequest,
    TriggerAIScoringRequest,
)
from app.services.ai_grading_service import AIGradingService
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("/trigger", response_model=AIScoreResultResponse)
async def trigger_ai_scoring(
    request: TriggerAIScoringRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """发起 AI 评分（HR/Admin）

    触发 AI 对指定答题记录进行评分，生成评分建议。
    AI 只提供建议，不直接修改成绩。
    """
    service = AIGradingService(db)
    record = service.trigger_ai_scoring(request.answer_record_id)
    result = service.get_ai_scoring_result(record.answer_record_id)
    return ApiResponse.success(data=result, message="AI 评分已生成")


@router.get("/results/{answer_record_id}", response_model=AIScoreResultResponse)
async def get_ai_scoring_result(
    answer_record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询 AI 评分结果（HR/Admin）

    返回 AI 评分建议详情，包括评分理由、知识点分析、置信度等。
    """
    service = AIGradingService(db)
    result = service.get_ai_scoring_result(answer_record_id)
    return ApiResponse.success(data=result)


@router.post("/confirm", response_model=AIScoreResultResponse)
async def confirm_ai_scoring(
    request: ConfirmAIScoringRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """HR 确认 AI 评分（HR/Admin）

    确认后：
    1. AI 评分记录状态变为 completed
    2. 答题记录的 score 更新为确认分数
    3. 不可再修改
    """
    service = AIGradingService(db)
    service.confirm_ai_scoring(
        answer_record_id=request.answer_record_id,
        confirmed_score=request.confirmed_score,
        reviewer_id=current_user.id,
        hr_remark=request.hr_remark,
    )
    result = service.get_ai_scoring_result(request.answer_record_id)
    return ApiResponse.success(data=result, message="评分已确认")


@router.post("/reject", response_model=AIScoreResultResponse)
async def reject_ai_scoring(
    request: RejectAIScoringRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """HR 拒绝 AI 评分（HR/Admin）

    拒绝后：
    1. AI 评分记录状态变为 rejected
    2. 可重新触发 AI 评分
    """
    service = AIGradingService(db)
    service.reject_ai_scoring(
        answer_record_id=request.answer_record_id,
        reviewer_id=current_user.id,
        hr_remark=request.hr_remark,
    )
    result = service.get_ai_scoring_result(request.answer_record_id)
    return ApiResponse.success(data=result, message="评分已拒绝")


@router.get("/status/{answer_record_id}", response_model=AIScoringStatusResponse)
async def get_ai_scoring_status(
    answer_record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询 AI 评分状态（HR/Admin）"""
    service = AIGradingService(db)
    result = service.get_ai_scoring_status(answer_record_id)
    return ApiResponse.success(data=result)


@router.get("/list", response_model=AIScoreListResponse)
async def list_ai_scores(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(default=None, description="状态筛选：pending/ai_scored/completed/rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取 AI 评分记录列表（HR/Admin）

    默认显示待审核的评分记录（ai_scored/hr_confirmed）
    """
    service = AIGradingService(db)
    result = service.get_pending_ai_scores(
        page=page,
        page_size=page_size,
        status=status,
    )
    return ApiResponse.success(data=result)
