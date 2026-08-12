"""
考试参与人员管理端点
所有接口均需 JWT + HR/Admin 权限
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_hr_or_admin
from app.db.session import get_db
from app.exceptions import NotFoundException
from app.models.user import User
from app.schemas.participant import (
    ParticipantBatchCreate,
    ParticipantCountResponse,
    ParticipantCreate,
    ParticipantListItem,
    ParticipantResponse,
    ParticipantUpdateStatus,
)
from app.services.exam_service import ExamService
from app.services.participant_service import ExamParticipantService
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("/exams/{exam_id}/participants", status_code=201)
async def add_participant(
    exam_id: int,
    data: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """添加单个考试参与人员"""
    service = ExamParticipantService(db)
    participant = service.add_participant(
        exam_id=exam_id,
        candidate_name=data.candidate_name,
        candidate_phone=data.candidate_phone,
        candidate_email=data.candidate_email,
        user_id=data.user_id,
    )
    return ApiResponse.created(
        data=ParticipantResponse.model_validate(participant).model_dump()
    )


@router.post("/exams/{exam_id}/participants/batch", status_code=201)
async def add_participants_batch(
    exam_id: int,
    data: ParticipantBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """批量添加考试参与人员"""
    service = ExamParticipantService(db)
    participants = [p.model_dump() for p in data.participants]
    success_count, errors = service.add_participants_batch(
        exam_id=exam_id,
        participants=participants,
    )
    return ApiResponse.success(
        data={
            "success_count": success_count,
            "errors": errors,
            "total": len(participants),
        }
    )


@router.get("/exams/{exam_id}/participants")
async def list_participants(
    exam_id: int,
    status: str | None = Query(default=None, description="状态筛选"),
    keyword: str | None = Query(default=None, description="搜索关键词（姓名/手机/邮箱）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询考试参与人员列表"""
    service = ExamParticipantService(db)
    items, total = service.list_participants(
        exam_id=exam_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/exams/{exam_id}/participants/count")
async def get_participant_count(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """获取考试参与人员统计"""
    service = ExamParticipantService(db)
    count_data = service.get_participant_count(exam_id)
    return ApiResponse.success(
        data=ParticipantCountResponse(**count_data).model_dump()
    )


@router.get("/participants/{participant_id}")
async def get_participant(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """查询单个参与人员详情"""
    service = ExamParticipantService(db)
    participant = service.get_participant(participant_id)
    return ApiResponse.success(
        data=ParticipantResponse.model_validate(participant).model_dump()
    )


@router.delete("/participants/{participant_id}")
async def remove_participant(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """删除参与人员（只能删除未参加考试的人员）"""
    service = ExamParticipantService(db)
    service.remove_participant(participant_id)
    return ApiResponse.success(message="删除成功")


@router.put("/participants/{participant_id}/status")
async def update_participant_status(
    participant_id: int,
    data: ParticipantUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """更新参与人员状态"""
    service = ExamParticipantService(db)
    participant = service.update_participant_status(
        participant_id=participant_id,
        status=data.status,
    )
    return ApiResponse.success(
        data=ParticipantResponse.model_validate(participant).model_dump()
    )


@router.post("/exams/{exam_id}/participants/sync")
async def sync_participant_status(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """同步参与人员状态（从 ExamRecord 获取）"""
    service = ExamParticipantService(db)
    updated_count = service.sync_status_from_exam_record(exam_id)
    return ApiResponse.success(
        data={"updated_count": updated_count},
        message=f"同步完成，更新 {updated_count} 条记录",
    )
