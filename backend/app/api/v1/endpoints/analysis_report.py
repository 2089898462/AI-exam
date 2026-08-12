"""
候选人分析报告 API 端点
提供分析报告的生成、查询、审核等接口
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import require_hr_or_admin
from app.models import User
from app.schemas.analysis_report import (
    AnalysisReportListResponse,
    AnalysisReportResponse,
    AnalysisReviewRequest,
)
from app.services.analysis_service import get_analysis_service

router = APIRouter(tags=["候选人分析报告"])


@router.post(
    "/exam-records/{exam_record_id}/generate",
    response_model=AnalysisReportResponse,
    summary="生成候选人分析报告",
    description="基于考试记录和 AI 评分结果生成候选人能力分析报告。如果报告已存在则直接返回。",
)
async def generate_analysis_report(
    exam_record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """生成候选人分析报告（HR 或管理员权限）"""
    service = get_analysis_service(db)
    try:
        report = service.generate_report(exam_record_id)
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{report_id}",
    response_model=AnalysisReportResponse,
    summary="获取分析报告详情",
)
async def get_analysis_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取分析报告详情（HR 或管理员权限）"""
    service = get_analysis_service(db)
    return service.get_report(report_id)


@router.get(
    "",
    response_model=list[AnalysisReportListResponse],
    summary="获取分析报告列表",
)
async def list_analysis_reports(
    candidate_id: Optional[int] = Query(None, description="候选人 ID"),
    status: Optional[str] = Query(None, description="报告状态：pending/generated/reviewed"),
    skip: int = Query(0, ge=0, description="起始位置"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取分析报告列表（HR 或管理员权限）"""
    service = get_analysis_service(db)
    return service.list_reports(
        candidate_id=candidate_id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/exam-records/{exam_record_id}",
    response_model=AnalysisReportResponse | None,
    summary="根据考试记录获取分析报告",
)
async def get_report_by_exam_record(
    exam_record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """根据考试记录获取分析报告（HR 或管理员权限）"""
    service = get_analysis_service(db)
    return service.get_report_by_exam_record(exam_record_id)


@router.post(
    "/{report_id}/review",
    response_model=AnalysisReportResponse,
    summary="HR 审核分析报告",
)
async def review_analysis_report(
    report_id: int,
    request: AnalysisReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """HR 审核分析报告（HR 或管理员权限）"""
    service = get_analysis_service(db)
    return service.review_report(
        report_id=report_id,
        reviewed_by=current_user.id,
        hr_remark=request.hr_remark,
    )
