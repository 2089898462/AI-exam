"""
v1 版本 API 路由注册中心
所有业务 endpoint 在此统一注册
"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.exam_records import router as exam_record_router
from app.api.v1.endpoints.exam_records import hr_router as exam_record_hr_router
from app.api.v1.endpoints.exams import router as exam_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.questions import router as question_router

v1_router = APIRouter()

v1_router.include_router(health_router, prefix="/health", tags=["系统"])
v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
v1_router.include_router(exam_router, prefix="/exams", tags=["考试管理"])
v1_router.include_router(question_router, prefix="/questions", tags=["题目管理"])
v1_router.include_router(exam_record_router, prefix="/exam-records", tags=["候选人考试记录"])
v1_router.include_router(exam_record_hr_router, prefix="/exams", tags=["考试记录管理"])
