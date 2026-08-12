"""
v1 版本 API 路由注册中心
所有业务 endpoint 在此统一注册
"""
from fastapi import APIRouter

from app.api.v1.endpoints.ai_call_logs import router as ai_call_logs_router
from app.api.v1.endpoints.ai_grading import router as ai_grading_router
from app.api.v1.endpoints.ai_scoring import router as ai_scoring_router
from app.api.v1.endpoints.analysis_report import router as analysis_report_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.candidates import router as candidates_router
from app.api.v1.endpoints.exam_records import router as exam_record_router
from app.api.v1.endpoints.exam_records import hr_router as exam_record_hr_router
from app.api.v1.endpoints.exams import router as exam_router
from app.api.v1.endpoints.grading_results import router as grading_results_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.knowledge_base import router as knowledge_base_router
from app.api.v1.endpoints.participants import router as participant_router
from app.api.v1.endpoints.questions import router as question_router
from app.api.v1.endpoints.reports import router as report_router
from app.api.v1.endpoints.templates import router as template_router

v1_router = APIRouter()

v1_router.include_router(health_router, prefix="/health", tags=["系统"])
v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
v1_router.include_router(exam_router, prefix="/exams", tags=["考试管理"])
v1_router.include_router(question_router, prefix="/questions", tags=["题目管理"])
v1_router.include_router(template_router, prefix="/templates", tags=["试卷模板管理"])
v1_router.include_router(participant_router, tags=["考试人员管理"])
v1_router.include_router(exam_record_router, prefix="/exam-records", tags=["候选人考试记录"])
v1_router.include_router(exam_record_hr_router, prefix="/exams", tags=["考试记录管理"])
v1_router.include_router(grading_results_router, prefix="/grading", tags=["评分结果查询"])
v1_router.include_router(ai_scoring_router, prefix="/ai-scoring", tags=["AI 评分"])
v1_router.include_router(ai_grading_router, prefix="/ai-grading", tags=["AI 阅卷管理"])
v1_router.include_router(report_router, prefix="/reports", tags=["AI 报告管理"])
v1_router.include_router(candidates_router, prefix="", tags=["候选人历史查询"])
v1_router.include_router(ai_call_logs_router, prefix="", tags=["AI 调用审计"])
v1_router.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["知识库管理"])
v1_router.include_router(analysis_report_router, prefix="/analysis-reports", tags=["候选人分析报告"])
