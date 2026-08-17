"""
评分结果端点
HR 后台查询评分结果
包括评分结果列表、详情查询和HR复核
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.grading import (
    GradingResultDetailResponse,
    GradingResultListResponse,
    HRReviewUpdateRequest,
)
from app.services.grading_service import GradingService
from app.utils.response import ApiResponse

router = APIRouter()


@router.get("/results", response_model=GradingResultListResponse)
async def get_grading_results(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    exam_id: int | None = Query(default=None, description="考试ID筛选"),
    status: str | None = Query(default=None, description="评分状态筛选: pending/grading/completed/failed"),
    keyword: str | None = Query(default=None, description="候选人姓名/手机/邮箱搜索"),
    start_date: str | None = Query(default=None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取评分结果列表（HR/Admin）

    支持按考试、状态、候选人姓名搜索、日期范围筛选
    """
    service = GradingService(db)
    result = service.get_grading_results(
        page=page,
        page_size=page_size,
        exam_id=exam_id,
        status=status,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
    )
    return ApiResponse.success(data=result)


@router.get("/results/{exam_record_id}", response_model=GradingResultDetailResponse)
async def get_grading_result_detail(
    exam_record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取评分结果详情（HR/Admin）

    包含：评分信息、候选人信息、答题详情、统计信息
    """
    service = GradingService(db)
    result = service.get_grading_result_detail(exam_record_id)
    return ApiResponse.success(data=result)


@router.put("/results/{exam_record_id}/review", response_model=GradingResultDetailResponse)
async def update_hr_review(
    exam_record_id: int,
    data: HRReviewUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """更新HR复核分数（HR/Admin）

    HR输入复核分数和备注，保存到评分记录中
    最终成绩优先显示HR复核分数
    """
    service = GradingService(db)
    result = service.update_hr_review(
        exam_record_id=exam_record_id,
        review_score=data.review_score,
        review_comment=data.review_comment,
    )
    return ApiResponse.success(data=result)
