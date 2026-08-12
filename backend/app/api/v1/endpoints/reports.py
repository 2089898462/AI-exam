"""
报告管理 API 端点
供 HR 查看和管理 AI 报告
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.exceptions import BusinessException, NotFoundException
from app.models.user import User
from app.schemas.report import (
    ReportGenerateRequest,
)
from app.services.report_service import ReportService
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("/generate")
async def generate_report(
    request: ReportGenerateRequest,
    db=Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """生成 AI 报告"""
    service = ReportService(db)

    try:
        report = service.generate_report_for_exam(
            exam_record_id=request.exam_record_id,
            model_used=request.model_used,
            prompt_version=request.prompt_version,
        )

        response_data = _report_to_response(report)
        return ApiResponse.created(data=response_data, message="报告生成成功")

    except (NotFoundException, BusinessException) as e:
        raise
    except Exception as e:
        raise BusinessException(f"报告生成失败: {e}")


@router.get("/exam-records/{exam_record_id}")
async def get_report_by_exam_record(
    exam_record_id: int,
    db=Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """根据考试记录 ID 获取报告"""
    service = ReportService(db)

    report = service.get_report_by_exam_record(exam_record_id)
    if not report:
        return ApiResponse.success(data=None, message="暂无报告")

    response_data = _report_to_response(report)
    return ApiResponse.success(data=response_data)


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db=Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取报告详情"""
    service = ReportService(db)

    report = service.get_report_by_id(report_id)
    response_data = _report_to_response(report)
    return ApiResponse.success(data=response_data)


@router.get("")
async def list_reports(
    exam_id: Optional[int] = Query(default=None, description="考试 ID 筛选"),
    status: Optional[str] = Query(default=None, description="状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取报告列表"""
    service = ReportService(db)

    reports, total = service.list_reports(
        exam_id=exam_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    items = []
    for report in reports:
        item = _report_to_list_item(report, db)
        items.append(item)

    response_data = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return ApiResponse.success(data=response_data)


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db=Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """删除报告"""
    service = ReportService(db)
    service.delete_report(report_id)
    return ApiResponse.success(message="报告删除成功")


def _report_to_response(report) -> dict:
    """将 AiReport 模型转换为响应格式"""
    def _ensure_list(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def _ensure_dict(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    return {
        "id": report.id,
        "exam_record_id": report.exam_record_id,
        "summary": report.summary,
        "strengths": _ensure_list(report.strengths),
        "weaknesses": _ensure_list(report.weaknesses),
        "skill_analysis": _ensure_dict(report.skill_analysis),
        "interview_suggestions": _ensure_list(report.interview_suggestions),
        "recommendation": report.recommendation,
        "model_used": report.model_used,
        "prompt_version": report.prompt_version,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


def _report_to_list_item(report, db) -> dict:
    """将 AiReport 模型转换为列表项格式"""
    from app.models.exam_record import ExamRecord
    from app.models.exam import Exam

    exam_record = db.query(ExamRecord).filter(ExamRecord.id == report.exam_record_id).first()
    exam_id = exam_record.exam_id if exam_record else None
    exam_title = ""
    candidate_name = exam_record.candidate_name if exam_record else ""

    if exam_id:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if exam:
            exam_title = exam.title

    return {
        "id": report.id,
        "exam_record_id": report.exam_record_id,
        "exam_id": exam_id,
        "exam_title": exam_title,
        "candidate_name": candidate_name,
        "status": report.status,
        "recommendation": report.recommendation,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
