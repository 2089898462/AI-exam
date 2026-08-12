"""
AI 调用审计日志查询端点

提供 AI 调用日志的查询接口（仅管理员可用）。
用于安全审计和问题追溯。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_call_log import AiCallLogListResponse
from app.services.ai_call_log_service import AiCallLogService
from app.utils.response import ApiResponse

router = APIRouter()


@router.get("/ai-call-logs")
async def get_ai_call_logs(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    caller_user_id: int | None = Query(default=None, description="调用者 ID"),
    status: str | None = Query(default=None, description="状态：success/failed/error"),
    source: str | None = Query(default=None, description="来源：ai_agent/webhook/api"),
    start_time: datetime | None = Query(default=None, description="开始时间"),
    end_time: datetime | None = Query(default=None, description="结束时间"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """查询 AI 调用审计日志（仅管理员）

    用于安全审计和问题追溯。
    日志中仅包含脱敏后的请求/响应摘要，不包含敏感数据。
    """
    service = AiCallLogService(db)
    result = service.query_logs(
        current_user=current_user,
        page=page,
        page_size=page_size,
        caller_user_id=caller_user_id,
        status=status,
        source=source,
        start_time=start_time,
        end_time=end_time,
    )
    return ApiResponse.success(data=result)


@router.get("/ai-call-logs/{log_id}")
async def get_ai_call_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """查询单条 AI 调用日志详情（仅管理员）"""
    service = AiCallLogService(db)
    result = service.get_log_by_id(
        log_id=log_id,
        current_user=current_user,
    )
    if result is None:
        return ApiResponse.error(code=404, message="日志不存在")
    return ApiResponse.success(data=result)