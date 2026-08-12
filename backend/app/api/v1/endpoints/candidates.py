"""
候选人历史考试查询端点
提供候选人历史考试记录查询能力
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_authenticated, require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.exam_statistics import (
    CandidateHistoryByPhoneResponse,
    CandidateHistoryPaginatedResponse,
    CandidateHistoryResponse,
)
from app.services.exam_statistics_service import ExamStatisticsService
from app.utils.response import ApiResponse

router = APIRouter()


@router.get("/candidates/{candidate_id}/exam-history")
async def get_candidate_exam_history(
    candidate_id: int,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query(default="created_at", description="排序字段: created_at / submitted_at"),
    sort_order: str = Query(default="desc", description="排序方向: asc / desc"),
    status: str | None = Query(default=None, description="状态筛选: submitted / graded / in_progress"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """查询候选人历史考试记录（增强版：分页/排序/过滤）

    权限规则：
    - Admin/HR: 可查看任意候选人历史
    - Employee: 只能查看自己的历史

    支持：
    - 分页（page / page_size）
    - 时间排序（sort_by / sort_order）
    - 状态过滤（status）
    """
    service = ExamStatisticsService(db)

    # 使用增强版分页方法
    result = service.get_candidate_exam_history_paginated(
        candidate_id=candidate_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
    )
    return ApiResponse.success(data=result)


@router.get("/candidates/by-phone/exam-history")
async def get_candidate_history_by_phone(
    phone: str = Query(..., description="候选人手机号"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """通过手机号查询候选人历史考试记录（HR/Admin）

    支持查询非系统用户候选人（仅有手机号记录的候选人）
    """
    service = ExamStatisticsService(db)
    result = service.get_candidate_history_by_phone(
        phone=phone,
        current_user=current_user,
    )
    return ApiResponse.success(data=result)
