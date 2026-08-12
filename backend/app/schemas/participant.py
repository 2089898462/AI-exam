"""
考试参与人员 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class ParticipantCreate(BaseSchema):
    """创建参与人员请求"""
    candidate_name: str = Field(..., min_length=1, max_length=64, description="候选人姓名")
    candidate_phone: Optional[str] = Field(None, max_length=20, description="手机号")
    candidate_email: Optional[str] = Field(None, max_length=128, description="邮箱")
    user_id: Optional[int] = Field(None, description="关联系统用户ID")


class ParticipantBatchCreate(BaseSchema):
    """批量创建参与人员请求"""
    participants: list[ParticipantCreate] = Field(..., min_length=1, description="参与人员列表")


class ParticipantResponse(BaseSchema):
    """参与人员响应"""
    id: int
    exam_id: int
    user_id: Optional[int] = None
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    status: str
    created_at: datetime


class ParticipantListItem(BaseSchema):
    """参与人员列表项"""
    id: int
    exam_id: int
    user_id: Optional[int] = None
    candidate_name: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    status: str
    completed: bool = False
    exam_record_status: Optional[str] = None
    created_at: Optional[str] = None


class ParticipantListResponse(BaseSchema):
    """参与人员列表响应"""
    items: list[ParticipantListItem]
    total: int
    page: int
    page_size: int


class ParticipantCountResponse(BaseSchema):
    """参与人员统计响应"""
    total: int
    assigned: int
    not_started: int
    in_progress: int
    completed: int


class ParticipantUpdateStatus(BaseSchema):
    """更新参与人员状态请求"""
    status: str = Field(..., description="新状态: assigned/not_started/in_progress/submitted/completed")
