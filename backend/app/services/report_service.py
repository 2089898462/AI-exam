"""
报告业务 Service
负责报告的创建、查询、生成等业务逻辑
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.ai_report import AiReport
from app.models.exam_record import ExamRecord
from app.models.grading_record import GradingRecord
from app.services.ai_report_service import ai_report_service

logger = get_logger(__name__)


class ReportService:
    """报告业务 Service"""

    def __init__(self, db: Session):
        self.db = db

    def create_report(
        self,
        exam_record_id: int,
        report_data: dict,
        model_used: str = "qwen-plus",
        prompt_version: str = "1.0",
    ) -> AiReport:
        """创建 AI 报告

        Args:
            exam_record_id: 考试记录 ID
            report_data: 报告数据 (summary, strengths, weaknesses, ...)
            model_used: 使用的模型
            prompt_version: Prompt 版本

        Returns:
            AiReport: 创建的报告记录
        """
        # 检查考试记录是否存在
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        # 检查是否已有报告
        existing = self.db.query(AiReport).filter(
            AiReport.exam_record_id == exam_record_id
        ).first()
        if existing:
            # 更新现有报告
            return self.update_report(existing.id, report_data, model_used, prompt_version)

        # 创建新报告
        report = AiReport(
            exam_record_id=exam_record_id,
            summary=report_data.get("summary", ""),
            strengths=report_data.get("strengths", []),
            weaknesses=report_data.get("weaknesses", []),
            skill_analysis=report_data.get("skill_analysis", {}),
            interview_suggestions=report_data.get("interview_suggestions", []),
            recommendation=report_data.get("recommendation", "保留考虑"),
            model_used=model_used,
            prompt_version=prompt_version,
            status="completed",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def update_report(
        self,
        report_id: int,
        report_data: dict,
        model_used: str = "qwen-plus",
        prompt_version: str = "1.0",
    ) -> AiReport:
        """更新 AI 报告"""
        report = self.db.query(AiReport).filter(AiReport.id == report_id).first()
        if not report:
            raise NotFoundException("报告不存在")

        report.summary = report_data.get("summary", report.summary)
        report.strengths = report_data.get("strengths", [])
        report.weaknesses = report_data.get("weaknesses", [])
        report.skill_analysis = report_data.get("skill_analysis", {})
        report.interview_suggestions = report_data.get("interview_suggestions", [])
        report.recommendation = report_data.get("recommendation", report.recommendation)
        report.model_used = model_used
        report.prompt_version = prompt_version
        report.status = "completed"
        report.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report_by_exam_record(self, exam_record_id: int) -> AiReport | None:
        """根据考试记录 ID 获取报告"""
        return self.db.query(AiReport).filter(
            AiReport.exam_record_id == exam_record_id
        ).first()

    def get_report_by_id(self, report_id: int) -> AiReport:
        """根据 ID 获取报告"""
        report = self.db.query(AiReport).filter(AiReport.id == report_id).first()
        if not report:
            raise NotFoundException("报告不存在")
        return report

    def list_reports(
        self,
        exam_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AiReport], int]:
        """获取报告列表

        Returns:
            tuple: (报告列表, 总数)
        """
        query = self.db.query(AiReport)

        if status:
            query = query.filter(AiReport.status == status)

        total = query.count()
        reports = query.order_by(AiReport.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return reports, total

    def generate_report_for_exam(
        self,
        exam_record_id: int,
        model_used: str = "qwen-plus",
        prompt_version: str = "1.0",
    ) -> AiReport:
        """为考试记录生成 AI 报告

        Args:
            exam_record_id: 考试记录 ID
            model_used: 使用的模型
            prompt_version: Prompt 版本

        Returns:
            AiReport: 生成的报告
        """
        # 1. 获取考试记录和评分结果
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        # 2. 获取评分记录
        grading = self.db.query(GradingRecord).filter(
            GradingRecord.exam_record_id == exam_record_id
        ).first()
        if not grading or grading.status != "completed":
            raise BusinessException("考试评分未完成，无法生成报告")

        # 3. 准备考试结果数据
        exam_results = self._prepare_exam_results(exam_record_id, exam_record, grading)

        # 4. 调用 AI-Service 生成报告
        try:
            logger.info(
                f"开始生成 AI 报告: exam_record_id={exam_record_id}, "
                f"candidate={exam_record.candidate_name}, model={model_used}"
            )
            report_data = ai_report_service.generate_report(
                exam_results=json.dumps(exam_results, ensure_ascii=False),
                exam_title=exam_record.exam.title if exam_record.exam else "",
                candidate_name=exam_record.candidate_name,
                position=exam_record.exam.position if exam_record.exam else "",
                prompt_version=prompt_version,
            )
        except BusinessException as e:
            logger.error(f"AI 报告生成失败: exam_record_id={exam_record_id}, error={e.message}")
            raise e

        # 5. 保存报告
        report = self.create_report(
            exam_record_id=exam_record_id,
            report_data=report_data,
            model_used=model_used,
            prompt_version=report_data.get("prompt_version", prompt_version),
        )
        logger.info(
            f"AI 报告生成完成: report_id={report.id}, "
            f"exam_record_id={exam_record_id}, recommendation={report.recommendation}"
        )
        return report

    def _prepare_exam_results(
        self,
        exam_record_id: int,
        exam_record: ExamRecord,
        grading: GradingRecord,
    ) -> dict:
        """准备考试结果数据用于 AI 报告生成"""
        from app.models.answer_record import AnswerRecord
        from app.models.question import Question

        # 获取答题记录
        answers = self.db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == exam_record_id
        ).order_by(AnswerRecord.question_id).all()

        # 获取题目信息
        question_ids = [a.question_id for a in answers]
        questions = self.db.query(Question).filter(
            Question.id.in_(question_ids)
        ).all()
        question_map = {q.id: q for q in questions}

        # 构建答题详情
        answer_details = []
        for answer in answers:
            question = question_map.get(answer.question_id)
            detail = {
                "question_id": answer.question_id,
                "question_type": question.type if question else "unknown",
                "question_content": question.content[:100] if question else "",
                "score": float(answer.score) if answer.score is not None else 0,
                "full_score": float(question.score) if question else 0,
                "answer_content": answer.answer_content or "",
                "ai_score": float(answer.ai_score) if answer.ai_score is not None else None,
                "ai_confidence": float(answer.ai_confidence) if answer.ai_confidence is not None else None,
                "needs_review": answer.needs_review or False,
            }
            answer_details.append(detail)

        return {
            "exam_record_id": exam_record_id,
            "candidate_name": exam_record.candidate_name,
            "exam_title": exam_record.exam.title if exam_record.exam else "",
            "total_score": float(grading.total_score) if grading.total_score else 0,
            "auto_score": float(grading.auto_score) if grading.auto_score else 0,
            "ai_score": float(grading.ai_score) if grading.ai_score else 0,
            "passed": grading.passed or False,
            "answers": answer_details,
            "statistics": {
                "total_questions": len(answers),
                "answered_count": sum(1 for a in answers if a.answer_content and a.answer_content.strip()),
                "needs_review_count": sum(1 for a in answers if a.needs_review),
            },
        }

    def delete_report(self, report_id: int) -> None:
        """删除报告"""
        report = self.get_report_by_id(report_id)
        self.db.delete(report)
        self.db.commit()
