"""
AI 评分 API 端点
Backend 对外暴露的 AI 评分接口
"""
from fastapi import APIRouter, Depends

from app.core.permissions import require_hr_or_admin
from app.models.user import User
from app.schemas.ai_scoring import AIScoringRequest, AIScoringResponse
from app.services.ai_scoring_service import ai_scoring_service
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("/evaluate", response_model=AIScoringResponse)
async def evaluate_ai_scoring(
    data: AIScoringRequest,
    current_user: User = Depends(require_hr_or_admin),
):
    """执行 AI 评分（HR/Admin）

    调用 AI-Service 对主观题答案进行评分。
    当前仅支持单题评分，批量评分后续版本支持。
    """
    result = ai_scoring_service.evaluate_scoring(
        question=data.question,
        standard_answer=data.standard_answer,
        user_answer=data.user_answer,
        max_score=data.max_score,
        scoring_rules=data.scoring_rules,
    )
    return ApiResponse.success(data=result)


@router.get("/health")
async def check_ai_service_health(
    current_user: User = Depends(require_hr_or_admin),
):
    """检查 AI-Service 健康状态（HR/Admin）"""
    is_healthy = ai_scoring_service.check_service_health()
    return ApiResponse.success(data={
        "service": "ai-scoring",
        "status": "ok" if is_healthy else "unavailable",
        "available": is_healthy,
    })
