"""
候选人分析报告 Service
基于考试数据和 AI 评分结果，为 HR 提供招聘辅助分析能力

核心原则：
1. AI 只提供辅助分析，不参与招聘决策
2. AI 不能输出录用建议
3. AI 分析结果必须可追溯
4. AI 只能使用授权数据
5. 保留人工最终决定权

流程：
候选人考试数据 → AI 评分结果 → 评分知识点
    ↓
能力维度分析（专业知识、薄弱点、优势）
    ↓
生成辅助报告（面试建议、关注方向）
    ↓
保存分析结果（不每次重新生成）
"""
import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.ai_score_record import AIScoreRecord
from app.models.answer_record import AnswerRecord
from app.models.candidate_analysis_report import CandidateAnalysisReport
from app.models.exam import Exam
from app.models.exam_record import ExamRecord
from app.models.question import Question

logger = get_logger(__name__)


class AnalysisService:
    """候选人分析报告业务逻辑"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 报告生成 ====================

    def generate_report(self, exam_record_id: int) -> CandidateAnalysisReport:
        """生成候选人分析报告

        获取考试数据和 AI 评分结果，进行能力分析并保存报告。
        如果报告已存在则返回现有报告（不重复生成）。

        Args:
            exam_record_id: 考试记录 ID

        Returns:
            CandidateAnalysisReport 实体

        Raises:
            NotFoundException: 考试记录不存在
            BusinessException: AI 评分不存在或 AI 分析失败
        """
        # 1. 检查报告是否已存在
        existing = self.db.query(CandidateAnalysisReport).filter(
            CandidateAnalysisReport.exam_record_id == exam_record_id
        ).first()
        if existing:
            logger.info(f"分析报告已存在: report_id={existing.id}, exam_record_id={exam_record_id}")
            return existing

        # 2. 获取考试记录
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException(f"考试记录不存在: {exam_record_id}")

        # 3. 获取所有答题记录
        answer_records = self.db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == exam_record_id
        ).all()

        if not answer_records:
            raise BusinessException("暂无答题记录，无法生成分析报告。")

        answer_record_ids = [ar.id for ar in answer_records]

        # 4. 获取关联的 AI 评分结果（通过 answer_record_id 关联）
        ai_scores = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id.in_(answer_record_ids),
            AIScoreRecord.review_status.in_(["ai_scored", "hr_confirmed", "completed"]),
        ).all()

        if not ai_scores:
            raise BusinessException(
                "暂无 AI 评分结果，无法生成分析报告。请先触发 AI 评分。"
            )

        # 5. 获取考试信息
        exam = self.db.query(Exam).filter(Exam.id == exam_record.exam_id).first()

        # 6. 收集分析数据
        analysis_data = self._collect_analysis_data(ai_scores, answer_records, exam)

        # 7. 执行 AI 分析
        try:
            analysis_result = self._run_ai_analysis(analysis_data, exam)
        except Exception as e:
            logger.error(f"AI 分析失败: {str(e)}")
            raise BusinessException(f"AI 分析失败: {str(e)}")

        # 8. 创建分析报告
        # 获取候选人系统用户 ID（如果参与者关联了系统用户）
        candidate_user_id = None
        if exam_record.participant_id:
            from app.models.exam_participant import ExamParticipant
            participant = self.db.query(ExamParticipant).filter(
                ExamParticipant.id == exam_record.participant_id
            ).first()
            if participant and participant.user_id:
                candidate_user_id = participant.user_id

        report = CandidateAnalysisReport(
            exam_record_id=exam_record_id,
            participant_id=exam_record.participant_id,
            candidate_user_id=candidate_user_id,
            overall_score=analysis_result.get("overall_score", 0.0),
            analysis_summary=analysis_result.get("analysis_summary", ""),
            knowledge_mastery=json.dumps(
                analysis_result.get("knowledge_mastery", {}), ensure_ascii=False
            ),
            strengths=json.dumps(
                analysis_result.get("strengths", []), ensure_ascii=False
            ),
            weak_points=json.dumps(
                analysis_result.get("weak_points", []), ensure_ascii=False
            ),
            interview_focus=json.dumps(
                analysis_result.get("interview_focus", []), ensure_ascii=False
            ),
            suggested_questions=json.dumps(
                analysis_result.get("suggested_questions", []), ensure_ascii=False
            ),
            model_name=analysis_result.get("model_name", ""),
            analysis_version="v1",
            status="generated",
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        logger.info(
            f"候选人分析报告生成成功: report_id={report.id}, exam_record_id={exam_record_id}"
        )
        return report

    # ==================== 报告查询 ====================

    def get_report(self, report_id: int) -> CandidateAnalysisReport:
        """获取单个分析报告"""
        report = self.db.query(CandidateAnalysisReport).filter(
            CandidateAnalysisReport.id == report_id
        ).first()
        if not report:
            raise NotFoundException(f"分析报告不存在: {report_id}")
        return report

    def get_report_by_exam_record(self, exam_record_id: int) -> CandidateAnalysisReport | None:
        """根据考试记录获取分析报告"""
        return self.db.query(CandidateAnalysisReport).filter(
            CandidateAnalysisReport.exam_record_id == exam_record_id
        ).first()

    def list_reports(
        self,
        participant_id: int | None = None,
        candidate_user_id: int | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[CandidateAnalysisReport]:
        """获取分析报告列表"""
        query = self.db.query(CandidateAnalysisReport)

        if participant_id:
            query = query.filter(CandidateAnalysisReport.participant_id == participant_id)
        if candidate_user_id:
            query = query.filter(CandidateAnalysisReport.candidate_user_id == candidate_user_id)
        if status:
            query = query.filter(CandidateAnalysisReport.status == status)

        return (
            query.order_by(CandidateAnalysisReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ==================== 报告审核 ====================

    def review_report(
        self, report_id: int, reviewed_by: int, hr_remark: str
    ) -> CandidateAnalysisReport:
        """HR 审核分析报告"""
        report = self.get_report(report_id)
        report.status = "reviewed"
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.now()
        report.hr_remark = hr_remark
        self.db.commit()
        self.db.refresh(report)
        return report

    # ==================== 私有方法 ====================

    def _collect_analysis_data(
        self,
        ai_scores: list[AIScoreRecord],
        answer_records: list[AnswerRecord],
        exam: Exam | None,
    ) -> dict[str, Any]:
        """收集分析所需的数据"""
        total_score = 0.0
        max_score_total = 0.0
        all_matched_points = []
        all_missing_points = []
        question_analyses = []

        for score in ai_scores:
            if score.review_status == "completed":
                total_score += float(score.ai_score or 0)
            max_score_total += float(score.max_score or 0)

            if score.matched_points:
                try:
                    matched = json.loads(score.matched_points)
                    all_matched_points.extend(matched)
                except json.JSONDecodeError:
                    pass

            if score.missing_points:
                try:
                    missing = json.loads(score.missing_points)
                    all_missing_points.extend(missing)
                except json.JSONDecodeError:
                    pass

            question_analyses.append(
                {
                    "answer_record_id": score.answer_record_id,
                    "score": score.ai_score,
                    "max_score": score.max_score,
                    "confidence": score.confidence,
                    "reason": score.score_reason,
                    "matched_points": score.matched_points,
                    "missing_points": score.missing_points,
                }
            )

        # 获取考试题目信息
        question_ids = [ar.question_id for ar in answer_records]
        questions = (
            self.db.query(Question)
            .filter(Question.id.in_(question_ids))
            .all()
        )
        question_map = {q.id: q for q in questions}

        question_info = []
        for ar in answer_records:
            question = question_map.get(ar.question_id)
            if question:
                question_info.append(
                    {
                        "id": question.id,
                        "content": question.content[:100],
                        "score": question.score,
                        "type": question.type,
                    }
                )

        return {
            "exam_id": exam.id if exam else None,
            "exam_title": exam.title if exam else "",
            "exam_position": exam.position if exam else "",
            "total_score": total_score,
            "max_score_total": max_score_total,
            "score_percentage": (
                (total_score / max_score_total * 100)
                if max_score_total > 0
                else 0
            ),
            "matched_points": list(set(all_matched_points)),
            "missing_points": list(set(all_missing_points)),
            "question_analyses": question_analyses,
            "question_info": question_info,
        }

    def _run_ai_analysis(
        self, analysis_data: dict[str, Any], exam: Exam | None
    ) -> dict[str, Any]:
        """执行 AI 分析（本地规则引擎）

        基于考试数据和 AI 评分结果，生成候选人能力分析。
        AI 只提供辅助分析，不参与招聘决策。
        """
        return self._perform_local_analysis(analysis_data, exam)

    def _perform_local_analysis(
        self, analysis_data: dict[str, Any], exam: Exam | None
    ) -> dict[str, Any]:
        """本地规则分析实现

        基于规则生成分析结果，不依赖外部 AI 服务。
        """
        percentage = analysis_data["score_percentage"]
        matched = analysis_data["matched_points"]
        missing = analysis_data["missing_points"]
        position = exam.position if exam else "通用"

        # 1. 知识掌握度
        knowledge_mastery = {}
        for point in matched:
            if point in missing:
                knowledge_mastery[point] = "基本了解"
            else:
                knowledge_mastery[point] = "掌握"
        for point in missing:
            if point not in matched:
                knowledge_mastery[point] = "薄弱"

        # 2. 优势分析
        strengths = []
        if percentage >= 80:
            strengths.append(f"整体得分较高（{percentage:.0f}%），基础扎实")
        elif percentage >= 60:
            strengths.append(f"整体表现合格（{percentage:.0f}%），具备基本能力")
        if matched:
            top_points = matched[:3]
            strengths.append(f"在 {', '.join(top_points)} 方面表现优秀")
        if len(missing) <= 2:
            strengths.append("知识覆盖面较广，缺失知识点少")

        # 3. 薄弱点分析
        weak_points = []
        if percentage < 60:
            weak_points.append(f"整体得分偏低（{percentage:.0f}%），需要加强学习")
        if missing:
            for mp in missing[:3]:
                weak_points.append(f"缺少 {mp} 相关知识")
        if percentage < 75 and percentage >= 60:
            weak_points.append("部分知识点掌握不够深入")

        # 4. 面试关注点
        interview_focus = []
        if missing:
            for mp in missing[:3]:
                interview_focus.append(f"深入了解 {mp} 的实际应用")
        if percentage < 70:
            interview_focus.append("考察基础概念理解深度")
        if matched:
            interview_focus.append(f"验证 {matched[0]} 相关的项目经验")
        interview_focus.append("考察问题解决能力和学习潜力")

        # 5. 建议问题
        suggested_questions = []
        if missing:
            suggested_questions.append(f"请描述一下{missing[0]}的实际应用场景")
            if len(missing) > 1:
                suggested_questions.append(
                    f"如何在项目中处理{missing[1]}相关的问题？"
                )
        if matched:
            suggested_questions.append(
                f"请举例说明你在{matched[0]}方面的项目经验"
            )
        suggested_questions.append("描述一个你遇到过的技术难题及解决方法")

        # 6. 分析摘要
        if percentage >= 80:
            summary = (
                f"候选人在{position}相关考试中表现优秀（{percentage:.0f}%），"
                f"知识掌握全面，可重点考察项目实践深度。"
            )
        elif percentage >= 60:
            summary = (
                f"候选人在{position}相关考试中基本合格（{percentage:.0f}%），"
                f"部分知识点需要加强，建议面试关注薄弱环节。"
            )
        else:
            summary = (
                f"候选人在{position}相关考试中得分较低（{percentage:.0f}%），"
                f"基础有待加强，建议面试评估学习潜力。"
            )

        return {
            "overall_score": analysis_data["total_score"],
            "analysis_summary": summary,
            "knowledge_mastery": knowledge_mastery,
            "strengths": strengths[:5],
            "weak_points": weak_points[:5],
            "interview_focus": interview_focus[:5],
            "suggested_questions": suggested_questions[:5],
            "model_name": "local-analysis-v1",
        }


def get_analysis_service(db: Session) -> AnalysisService:
    """获取 AnalysisService 实例"""
    return AnalysisService(db=db)
