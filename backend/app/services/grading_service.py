"""
评分记录Service
管理考试评分记录的创建、状态流转和查询
支持客观题自动评分 + 主观题 AI 评分混合流程
"""
import asyncio
import json
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.answer_record import AnswerRecord
from app.models.exam import Exam
from app.models.exam_monitor_summary import ExamMonitorSummary
from app.models.exam_record import ExamRecord
from app.models.grading_record import GradingRecord
from app.models.question import Question
from app.models.question_score_rule import QuestionScoreRule
from app.services.ai_scoring_service import ai_scoring_service
from app.services.base import BaseService
from app.services.objective_grader import (
    calculate_auto_score,
    grade_question,
    is_objective_question,
)

logger = get_logger(__name__)


class GradingService(BaseService[GradingRecord]):
    """评分记录业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, GradingRecord)

    def create_grading_record(
        self,
        exam_record_id: int,
        grading_type: str = "auto",
    ) -> GradingRecord:
        """创建评分记录

        前置条件：
        - 考试记录存在
        - 考试记录状态为 submitted 或 graded
        - 评分记录不存在（一对一关系）

        初始状态：pending（待评分）
        """
        record = self.db.query(ExamRecord).filter(ExamRecord.id == exam_record_id).first()
        if not record:
            raise NotFoundException("考试记录不存在")

        # 检查状态
        if record.status not in ("submitted", "graded"):
            raise BusinessException("考试尚未提交，无法创建评分记录")

        # 检查是否已存在评分记录
        existing = self.db.query(GradingRecord).filter(
            GradingRecord.exam_record_id == exam_record_id
        ).first()
        if existing:
            raise BusinessException("该考试记录已存在评分记录")

        grading_record = GradingRecord(
            exam_record_id=exam_record_id,
            status="pending",
            grading_type=grading_type,
        )
        self.db.add(grading_record)
        try:
            self.db.commit()
            self.db.refresh(grading_record)
        except Exception:
            self.db.rollback()
            logger.error(f"创建评分记录失败: exam_record_id={exam_record_id}")
            raise
        logger.info(f"创建评分记录: exam_record_id={exam_record_id}, grading_id={grading_record.id}")
        return grading_record

    def get_grading_by_record_id(self, exam_record_id: int) -> GradingRecord | None:
        """根据考试记录ID查询评分记录"""
        return self.db.query(GradingRecord).filter(
            GradingRecord.exam_record_id == exam_record_id
        ).first()

    def start_grading(self, grading_id: int) -> GradingRecord:
        """开始评分

        状态流转：pending → grading
        记录 started_at 时间戳
        """
        grading = self.get(grading_id)
        if not grading:
            raise NotFoundException("评分记录不存在")

        if grading.status != "pending":
            raise BusinessException(f"评分记录状态为 {grading.status}，无法开始评分")

        grading.status = "grading"
        grading.started_at = datetime.now()
        self.db.commit()
        self.db.refresh(grading)
        return grading

    def complete_grading(
        self,
        grading_id: int,
        total_score: float,
        auto_score: float | None = None,
        ai_score: float | None = None,
        passed: bool | None = None,
    ) -> GradingRecord:
        """完成评分

        状态流转：grading → completed
        记录 completed_at 时间戳和评分结果
        """
        grading = self.get(grading_id)
        if not grading:
            raise NotFoundException("评分记录不存在")

        if grading.status not in ("pending", "grading"):
            raise BusinessException(f"评分记录状态为 {grading.status}，无法完成评分")

        grading.status = "completed"
        grading.completed_at = datetime.now()
        grading.total_score = total_score
        grading.auto_score = auto_score
        grading.ai_score = ai_score
        grading.passed = passed
        self.db.commit()
        self.db.refresh(grading)
        return grading

    def fail_grading(self, grading_id: int, error_message: str) -> GradingRecord:
        """标记评分失败

        状态流转：grading → failed
        记录错误信息
        """
        grading = self.get(grading_id)
        if not grading:
            raise NotFoundException("评分记录不存在")

        grading.status = "failed"
        grading.completed_at = datetime.now()
        grading.error_message = error_message
        self.db.commit()
        self.db.refresh(grading)
        return grading

    def get_grading_status(self, exam_record_id: int) -> dict:
        """获取评分状态信息

        返回评分记录摘要，用于状态查询API
        """
        grading = self.get_grading_by_record_id(exam_record_id)
        if not grading:
            return {
                "exists": False,
                "exam_record_id": exam_record_id,
                "status": "not_started",
                "message": "尚未开始评分",
            }

        result = {
            "exists": True,
            "id": grading.id,
            "exam_record_id": grading.exam_record_id,
            "status": grading.status,
            "grading_type": grading.grading_type,
            "total_score": float(grading.total_score) if grading.total_score else None,
            "auto_score": float(grading.auto_score) if grading.auto_score else None,
            "ai_score": float(grading.ai_score) if grading.ai_score else None,
            "passed": grading.passed,
            "started_at": grading.started_at.isoformat() if grading.started_at else None,
            "completed_at": grading.completed_at.isoformat() if grading.completed_at else None,
            "error_message": grading.error_message,
        }
        return result

    def auto_grade_exam(self, exam_record_id: int) -> GradingRecord:
        """执行自动评分流程（客观题 + AI 主观题）

        流程：
        1. 创建评分记录（如果不存在）
        2. 加载答案记录和题目信息
        3. 逐题评分：
           - 客观题（单选/多选/判断）：自动比对评分
           - 主观题（简答）：调用 AI-Service 评分
        4. 保存评分结果到 answer_record
        5. 计算总分和是否及格
        6. 更新评分记录状态

        状态流转：pending → grading → completed
        """
        # 1. 确保评分记录存在
        grading = self.get_grading_by_record_id(exam_record_id)
        if not grading:
            grading = self.create_grading_record(exam_record_id, grading_type="hybrid")
        elif grading.status == "completed":
            raise BusinessException("评分已完成，无法重复评分")
        elif grading.status == "grading":
            raise BusinessException("评分进行中，请稍后再试")

        # 2. 开始评分
        try:
            grading = self.start_grading(grading.id)
            logger.info(f"开始自动评分: exam_record_id={exam_record_id}")

            # 3. 加载答案记录和题目信息
            exam_record = self.db.query(ExamRecord).filter(
                ExamRecord.id == exam_record_id
            ).first()
            if not exam_record:
                raise NotFoundException("考试记录不存在")

            answers = self._load_answers(exam_record_id)
            questions = self._load_questions(exam_record.exam_id)

            if not answers:
                # 无答案，直接完成评分为 0
                grading = self._complete_auto_grading(
                    grading, total_score=0.0, auto_score=0.0, ai_score=0.0,
                    answered_count=0, correct_count=0, unanswered_count=0,
                )
                self._update_exam_record_status(exam_record_id, "graded")
                return grading

            # 4. 逐题评分并保存
            grade_results = []
            ai_scores = []  # 收集 AI 评分用于计算
            for answer in answers:
                question_id = answer["question_id"]
                if question_id not in questions:
                    continue

                question = questions[question_id]
                question_type = question["type"]

                # 客观题自动评分
                if is_objective_question(question_type):
                    score, is_correct = grade_question(
                        question_type=question_type,
                        candidate_answer=answer.get("answer_content"),
                        standard_answer=question["answer"],
                        full_score=question["score"],
                    )
                    self._save_answer_score(answer["id"], score, is_correct)
                    grade_results.append({
                        "question_id": question_id,
                        "score": score,
                        "is_correct": is_correct,
                        "skipped": False,
                        "grading_method": "auto",
                    })
                # 主观题 AI 评分
                elif question_type == "short_answer":
                    ai_result = self._ai_grade_answer(
                        answer_record_id=answer["id"],
                        question=question,
                        candidate_answer=answer.get("answer_content") or "",
                    )
                    if ai_result:
                        ai_scores.append(ai_result["score"])
                        grade_results.append({
                            "question_id": question_id,
                            "score": ai_result["score"],
                            "is_correct": None,
                            "skipped": False,
                            "grading_method": "ai",
                        })
                    else:
                        grade_results.append({
                            "question_id": question_id,
                            "score": 0.0,
                            "is_correct": None,
                            "skipped": True,
                            "grading_method": "ai_failed",
                        })
                else:
                    # 不支持的题型
                    grade_results.append({
                        "question_id": question_id,
                        "score": None,
                        "is_correct": None,
                        "skipped": True,
                        "grading_method": "unknown",
                    })

            # 5. 计算总分
            auto_score = sum(
                r["score"] for r in grade_results
                if r["grading_method"] == "auto" and r["score"] is not None
            )
            total_ai_score = sum(ai_scores)
            total_score = auto_score + total_ai_score
            answered_count = sum(
                1 for r in grade_results if not r["skipped"] and r["score"] is not None
            )
            correct_count = sum(
                1 for r in grade_results
                if r.get("grading_method") == "auto" and r.get("is_correct")
            )
            unanswered_count = len([
                a for a in answers
                if not a.get("answer_content") or not a["answer_content"].strip()
            ])

            # 获取及格分数线
            pass_score = self._get_pass_score(exam_record.exam_id)
            passed = total_score >= pass_score

            # 6. 完成评分
            grading = self._complete_auto_grading(
                grading,
                total_score=total_score,
                auto_score=auto_score,
                ai_score=total_ai_score,
                answered_count=answered_count,
                correct_count=correct_count,
                unanswered_count=unanswered_count,
                passed=passed,
            )

            # 7. 更新考试记录状态
            self._update_exam_record_status(exam_record_id, "graded")

            logger.info(
                f"自动评分完成: exam_record_id={exam_record_id}, "
                f"total_score={total_score:.1f}, passed={passed}, "
                f"auto_score={auto_score:.1f}, ai_score={total_ai_score:.1f}"
            )
            return grading

        except Exception as e:
            # 评分失败
            error_msg = str(e)
            if "评分已完成" in error_msg or "评分进行中" in error_msg:
                raise
            grading = self.fail_grading(grading.id, error_msg)
            logger.error(f"自动评分失败: exam_record_id={exam_record_id}, error={error_msg}")
            raise BusinessException(f"自动评分失败：{error_msg}")

    def _ai_grade_answer(
        self,
        answer_record_id: int,
        question: dict,
        candidate_answer: str,
    ) -> dict | None:
        """使用 AI 对单道主观题评分

        Args:
            answer_record_id: 答题记录 ID
            question: 题目信息
            candidate_answer: 候选人答案

        Returns:
            dict: AI 评分结果，失败返回 None
        """
        # 空答案处理
        if not candidate_answer or not candidate_answer.strip():
            self._save_ai_score(
                answer_record_id=answer_record_id,
                score=0.0,
                reason="候选人未作答",
                confidence=1.0,
                needs_review=False,
                score_level="incorrect",
                question_type="short_answer",
                keyword_coverage=0.0,
            )
            return {"score": 0.0}

        try:
            # 调用 AI-Service
            result = ai_scoring_service.evaluate_scoring(
                question=question["content"],
                standard_answer=question.get("answer", ""),
                user_answer=candidate_answer,
                max_score=question["score"],
                scoring_rules=question.get("scoring_rules", ""),
            )

            # 保存 AI 评分结果
            self._save_ai_score(
                answer_record_id=answer_record_id,
                score=result["score"],
                reason=result.get("reason", ""),
                confidence=result.get("confidence", 0),
                needs_review=result.get("needs_review", False),
                missing_points=result.get("missing_points", []),
                matched_points=result.get("matched_points", []),
                prompt_version=result.get("prompt_version", "v3"),
                score_level=result.get("score_level", ""),
                question_type=result.get("question_type", ""),
                keyword_coverage=result.get("keyword_coverage"),
            )

            return result

        except BusinessException as e:
            # AI 服务调用失败，降级处理
            self._save_ai_score(
                answer_record_id=answer_record_id,
                score=0.0,
                reason=f"AI 评分失败: {e.message}",
                confidence=0.0,
                needs_review=True,
                prompt_version="v3",
                score_level="incorrect",
            )
            return None
        except Exception as e:
            # 其他异常
            self._save_ai_score(
                answer_record_id=answer_record_id,
                score=0.0,
                reason=f"AI 评分异常: {str(e)}",
                confidence=0.0,
                needs_review=True,
                prompt_version="v3",
                score_level="incorrect",
            )
            return None

    def _load_answers(self, exam_record_id: int) -> list[dict]:
        """加载答案记录"""
        answers = (
            self.db.query(AnswerRecord)
            .filter(AnswerRecord.exam_record_id == exam_record_id)
            .order_by(AnswerRecord.question_id.asc())
            .all()
        )
        return [
            {
                "id": a.id,
                "question_id": a.question_id,
                "answer_content": a.answer_content,
                "score": a.score,
                "is_correct": a.is_correct,
            }
            for a in answers
        ]

    def _load_questions(self, exam_id: int) -> dict[int, dict]:
        """加载题目信息"""
        questions = (
            self.db.query(Question)
            .filter(Question.exam_id == exam_id)
            .all()
        )
        return {
            q.id: {
                "id": q.id,
                "type": q.type,
                "content": q.content,
                "answer": q.answer,
                "score": float(q.score),
                "options": q.options,
            }
            for q in questions
        }

    def _save_answer_score(
        self,
        answer_record_id: int,
        score: float,
        is_correct: bool,
    ) -> None:
        """保存答题记录的评分结果"""
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if answer_record:
            answer_record.score = score
            answer_record.is_correct = is_correct
            self.db.commit()

    def _save_ai_score(
        self,
        answer_record_id: int,
        score: float,
        reason: str = "",
        confidence: float = 0.0,
        needs_review: bool = False,
        missing_points: list[str] | None = None,
        matched_points: list[str] | None = None,
        prompt_version: str = "v3",
        score_level: str = "",
        question_type: str = "",
        keyword_coverage: float | None = None,
    ) -> None:
        """保存 AI 评分结果到答题记录

        Args:
            answer_record_id: 答题记录 ID
            score: AI 评分分数
            reason: 评分理由
            confidence: 置信度
            needs_review: 是否需要人工复核
            missing_points: 遗漏要点
            matched_points: 匹配的知识点
            prompt_version: 使用的 Prompt 版本
            score_level: 评分等级 (v3)
            question_type: 题型 (v3)
            keyword_coverage: 知识点覆盖率 (v3)
        """
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if answer_record:
            # 构建增强的评分理由，包含知识点分析
            enhanced_reason = reason
            if matched_points:
                enhanced_reason += f"\n\n覆盖知识点: {', '.join(matched_points)}"
            if missing_points:
                enhanced_reason += f"\n\n遗漏要点: {', '.join(missing_points)}"
            if keyword_coverage is not None:
                enhanced_reason += f"\n\n知识点覆盖率: {keyword_coverage:.0%}"

            # 获取题目满分用于计算评分等级
            question = self.db.query(Question).filter(
                Question.id == answer_record.question_id
            ).first()
            full_score = float(question.score) if question and question.score else 10.0

            # 优先使用AI返回的score_level，否则本地计算
            if not score_level:
                score_level = self._calculate_score_level(score, full_score)

            answer_record.score = score
            answer_record.ai_score = score
            answer_record.score_level = score_level
            answer_record.ai_reason = enhanced_reason
            answer_record.ai_confidence = confidence
            answer_record.needs_review = needs_review
            answer_record.prompt_version = prompt_version
            answer_record.is_correct = score_level == "full_correct"
            answer_record.ai_comment = enhanced_reason
            answer_record.ai_status = "completed"
            answer_record.ai_scored_at = datetime.now()
            answer_record.matched_points = matched_points or []
            answer_record.missing_points = missing_points or []
            self.db.commit()

    def _calculate_score_level(self, score: float, full_score: float) -> str:
        """计算评分等级

        Args:
            score: 实际得分
            full_score: 满分

        Returns:
            str: 评分等级 (full_correct/partial_correct/incorrect)
        """
        if full_score <= 0:
            return "incorrect"

        ratio = score / full_score

        if ratio >= 0.9:
            return "full_correct"
        elif ratio >= 0.6:
            return "partial_correct"
        else:
            return "incorrect"

    def _get_pass_score(self, exam_id: int) -> float:
        """获取及格分数线

        优先从评分规则获取，默认为 60 分
        """
        rules = (
            self.db.query(QuestionScoreRule)
            .filter(
                QuestionScoreRule.exam_id == exam_id,
                QuestionScoreRule.is_enabled == True,
            )
            .all()
        )
        if rules:
            return max(rule.pass_score for rule in rules)
        return 60.0

    def _complete_auto_grading(
        self,
        grading: GradingRecord,
        total_score: float,
        auto_score: float,
        ai_score: float = 0.0,
        answered_count: int = 0,
        correct_count: int = 0,
        unanswered_count: int = 0,
        passed: bool | None = None,
    ) -> GradingRecord:
        """完成自动评分

        Args:
            grading: 评分记录
            total_score: 总分
            auto_score: 客观题得分
            ai_score: AI 主观题得分
            answered_count: 已答题数
            correct_count: 正确题数
            unanswered_count: 未答题数
            passed: 是否及格
        """
        grading.status = "completed"
        grading.completed_at = datetime.now()
        grading.total_score = total_score
        grading.auto_score = auto_score
        grading.ai_score = ai_score
        grading.passed = passed
        self.db.commit()
        self.db.refresh(grading)
        return grading

    def _update_exam_record_status(
        self,
        exam_record_id: int,
        status: str,
    ) -> None:
        """更新考试记录状态"""
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if exam_record:
            exam_record.status = status
            self.db.commit()

    def get_grading_results(
        self,
        page: int = 1,
        page_size: int = 10,
        exam_id: int | None = None,
        status: str | None = None,
        keyword: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """获取评分结果列表（HR 后台查询）

        Args:
            page: 页码
            page_size: 每页数量
            exam_id: 考试 ID 筛选
            status: 评分状态筛选
            keyword: 候选人姓名搜索
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: {items: list, total: int, page: int, page_size: int}
        """
        query = self.db.query(GradingRecord).join(
            ExamRecord, GradingRecord.exam_record_id == ExamRecord.id
        )

        # 筛选条件
        if exam_id:
            query = query.filter(ExamRecord.exam_id == exam_id)

        if status:
            query = query.filter(GradingRecord.status == status)

        if keyword:
            query = query.filter(
                or_(
                    ExamRecord.candidate_name.contains(keyword),
                    ExamRecord.candidate_email.contains(keyword),
                    ExamRecord.candidate_phone.contains(keyword),
                )
            )

        if start_date:
            query = query.filter(GradingRecord.created_at >= start_date)

        if end_date:
            query = query.filter(GradingRecord.created_at <= end_date)

        # 排序
        query = query.order_by(GradingRecord.created_at.desc())

        # 分页
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        # 转换为响应数据
        # S8.4.3: 批量查询监考汇总数据（避免N+1查询）
        exam_record_ids = [r.exam_record_id for r in records]
        monitor_map = {}
        if exam_record_ids:
            monitor_summaries = self.db.query(ExamMonitorSummary).filter(
                ExamMonitorSummary.exam_record_id.in_(exam_record_ids)
            ).all()
            monitor_map = {ms.exam_record_id: ms for ms in monitor_summaries}

        items = []
        for record in records:
            exam_record = self.db.query(ExamRecord).filter(
                ExamRecord.id == record.exam_record_id
            ).first()
            if exam_record:
                review_val = float(record.review_score) if record.review_score is not None else None
                # S8.4.3: 查找监考数据
                monitor_summary = monitor_map.get(record.exam_record_id)
                has_monitor = monitor_summary is not None
                risk_level = monitor_summary.risk_level if monitor_summary else "normal"
                items.append({
                    "id": record.id,
                    "exam_record_id": record.exam_record_id,
                    "exam_id": exam_record.exam_id,
                    "candidate_name": exam_record.candidate_name,
                    "candidate_phone": exam_record.candidate_phone,
                    "status": record.status,
                    "grading_type": record.grading_type,
                    "total_score": float(record.total_score) if record.total_score is not None else None,
                    "auto_score": float(record.auto_score) if record.auto_score is not None else None,
                    "ai_score": float(record.ai_score) if record.ai_score is not None else None,
                    "review_score": review_val,
                    "review_comment": record.review_comment,
                    "passed": record.passed,
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    # S8.4.3: 监考风险字段
                    "has_monitor_data": has_monitor,
                    "monitor_risk_level": risk_level,
                })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_grading_result_detail(
        self,
        exam_record_id: int,
    ) -> dict:
        """获取评分结果详情（含答题详情）

        Args:
            exam_record_id: 考试记录 ID

        Returns:
            dict: 评分结果详情数据
        """
        # 查询评分记录
        grading = self.get_grading_by_record_id(exam_record_id)
        if not grading:
            raise NotFoundException("评分记录不存在")

        # 查询考试记录
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        # 查询考试信息
        exam = self.db.query(Exam).filter(Exam.id == exam_record.exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        # 查询答题详情
        answers = self.db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == exam_record_id
        ).order_by(AnswerRecord.question_id.asc()).all()

        # 查询题目信息
        question_ids = [a.question_id for a in answers]
        questions = self.db.query(Question).filter(
            Question.id.in_(question_ids)
        ).all()
        question_map = {q.id: q for q in questions}

        # 构建答题详情列表
        answer_details = []
        for answer in answers:
            question = question_map.get(answer.question_id)
            detail = {
                "answer_id": answer.id,
                "question_id": answer.question_id,
                "question_type": question.type if question else "unknown",
                "question_content": question.content if question else "",
                "question_no": question.question_no if question else "",
                "candidate_answer": answer.answer_content,
                "standard_answer": question.answer if question else "",
                "score": float(answer.score) if answer.score is not None else None,
                "full_score": float(question.score) if question else 0,
                "is_correct": answer.is_correct,
                "score_level": answer.score_level,
                "options": question.options if question else None,
                # AI 评分详情
                "ai_score": float(answer.ai_score) if answer.ai_score is not None else None,
                "ai_reason": answer.ai_reason,
                "ai_confidence": float(answer.ai_confidence) if answer.ai_confidence is not None else None,
                "needs_review": answer.needs_review,
                "prompt_version": answer.prompt_version,
            }
            answer_details.append(detail)

        # 查询考试的总题数（从Question表获取，不是答题记录）
        total_questions = self.db.query(Question).filter(
            Question.exam_id == exam_record.exam_id
        ).count()

        # 统计信息
        answered_count = len([a for a in answers if a.answer_content and a.answer_content.strip()])
        correct_count = len([a for a in answers if a.is_correct])
        needs_review_count = len([a for a in answers if a.needs_review])

        # 查询监考汇总数据（兼容历史考试无监考数据的情况）
        monitor_data = self._get_monitor_summary_data(exam_record_id)

        # 生成监考分析数据（动态计算）
        monitor_analysis = self._generate_monitor_analysis(exam_record, monitor_data)

        result = {
            "grading_id": grading.id,
            "status": grading.status,
            "grading_type": grading.grading_type,
            "exam_record_id": exam_record_id,
            "exam_id": exam_record.exam_id,
            "exam_title": exam.title,
            "candidate_name": exam_record.candidate_name,
            "candidate_phone": exam_record.candidate_phone,
            "candidate_email": exam_record.candidate_email,
            "total_score": float(grading.total_score) if grading.total_score is not None else None,
            "auto_score": float(grading.auto_score) if grading.auto_score is not None else None,
            "ai_score": float(grading.ai_score) if grading.ai_score is not None else None,
            "review_score": float(grading.review_score) if grading.review_score is not None else None,
            "review_comment": grading.review_comment,
            "passed": grading.passed,
            "start_time": grading.started_at.isoformat() if grading.started_at else None,
            "complete_time": grading.completed_at.isoformat() if grading.completed_at else None,
            "error_message": grading.error_message,
            "statistics": {
                "total_questions": total_questions,
                "answered_count": answered_count,
                "correct_count": correct_count,
                "needs_review_count": needs_review_count,
                "correct_rate": round(correct_count / total_questions * 100, 1) if total_questions > 0 else 0,
            },
            "answers": answer_details,
            "monitor_data": monitor_data,
            "monitor_analysis": monitor_analysis,
        }
        return result

    def _get_monitor_summary_data(self, exam_record_id: int) -> dict:
        """获取监考汇总数据（兼容历史考试无监考数据的情况）

        Args:
            exam_record_id: 考试记录 ID

        Returns:
            dict: 监考数据，无数据时返回默认结构
        """
        # 默认结构（历史考试无监考数据时使用）
        default_data = {
            "has_monitor_data": False,
            "risk_level": "normal",
            "leave_count": 0,
            "total_duration": 0,
            "events": [],
        }

        try:
            monitor_summary = self.db.query(ExamMonitorSummary).filter(
                ExamMonitorSummary.exam_record_id == exam_record_id
            ).first()

            if monitor_summary is None:
                return default_data

            # S8.4.1: 解析详细事件列表（兼容新旧格式）
            events = []
            environment = None
            analysis = None  # S8.4.2: 新增
            if monitor_summary.detail_data:
                try:
                    parsed = json.loads(monitor_summary.detail_data)
                    # 判断数据格式：旧版为纯数组，新版为 {events: [...], environment: {...}}
                    if isinstance(parsed, list):
                        # 旧版格式：直接是事件数组
                        events = parsed
                    elif isinstance(parsed, dict):
                        # S8.4.1/S8.4.2 新版格式：结构化对象
                        events = parsed.get('events', [])
                        environment = parsed.get('environment', None)
                        analysis = parsed.get('analysis', None)  # S8.4.2: 解析分析数据
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "监考数据解析失败: record_id=%s", exam_record_id
                    )
                    events = []

            result = {
                "has_monitor_data": True,
                "risk_level": monitor_summary.risk_level,
                "leave_count": monitor_summary.leave_count,
                "total_duration": monitor_summary.total_duration,
                "events": events,
            }
            # S8.4.1: 附加环境采集数据（如有）
            if environment:
                result["environment"] = environment
            # S8.4.2: 附加异常分析数据（如有）
            if analysis:
                result["analysis"] = analysis

            return result

        except Exception as e:
            logger.error(
                "查询监考数据失败: record_id=%s, error=%s",
                exam_record_id,
                str(e),
            )
            # 异常时返回默认数据，不影响成绩详情查询
            return default_data

    def _generate_monitor_analysis(
        self,
        exam_record: ExamRecord,
        monitor_data: dict,
    ) -> dict:
        """生成监考数据分析（动态计算，不存储）

        S8.4.2 增强：支持异常行为标签和分析数据展示
        
        Args:
            exam_record: 考试记录
            monitor_data: 监考汇总数据
        
        Returns:
            dict: 监考分析数据
        """
        # 默认结构（无监考数据时使用）
        default_analysis = {
            "has_analysis": False,
            "exam_duration": 0,
            "leave_ratio": 0.0,
            "max_single_duration": 0,
            "average_leave_duration": 0.0,
            "risk_reason": "",
            "behavior_tags": [],  # S8.4.2: 新增
            "behavior_details": [],  # S8.4.2: 新增
            "review_suggestion": "",  # S8.4.3-b: 新增
        }

        try:
            # 无监考数据，返回默认
            if not monitor_data or not monitor_data.get("has_monitor_data", False):
                return default_analysis

            # 计算考试总时长（秒）
            exam_duration = self._calc_exam_duration(exam_record)

            # 从monitor_data获取基础数据
            leave_count = monitor_data.get("leave_count", 0)
            total_duration = monitor_data.get("total_duration", 0)
            events = monitor_data.get("events", [])
            risk_level = monitor_data.get("risk_level", "normal")
            
            # S8.4.2: 获取存储的异常分析数据
            stored_analysis = monitor_data.get("analysis", {})
            behavior_tags = list(stored_analysis.get("behavior_tags", []))
            stored_risk_reasons = stored_analysis.get("risk_reason", [])

            # S8.4.5: 根据事件类型补充中文行为标签（历史数据无存储标签时也能识别异常）
            event_types = {e.get("type", "") for e in events} if events else set()
            if "leave_recovered" in event_types and "异常中断恢复" not in behavior_tags:
                behavior_tags.append("异常中断恢复")
            if "network_offline" in event_types and "网络异常" not in behavior_tags:
                behavior_tags.append("网络异常")
            if "orientation_change" in event_types and "设备方向变化" not in behavior_tags:
                behavior_tags.append("设备方向变化")
            
            # S8.4.2: 获取已计算的指标（如有）
            max_single_duration = stored_analysis.get("max_single_duration", 0)
            if max_single_duration == 0:
                max_single_duration = self._calc_max_single_duration(events)
            
            leave_frequency = stored_analysis.get("leave_frequency", 0)
            rapid_trips = stored_analysis.get("rapid_trips", 0)
            max_leave_density = stored_analysis.get("max_leave_density", 0.0)

            # 计算离开时间占比（%）
            leave_ratio = self._calc_leave_ratio(total_duration, exam_duration)

            # 计算平均每次离开时长（秒）
            average_leave_duration = self._calc_average_leave_duration(
                total_duration, leave_count
            )

            # S8.4.2: 生成增强版风险原因说明
            risk_reason = self._generate_risk_reason_v2(
                risk_level=risk_level,
                leave_count=leave_count,
                total_duration=total_duration,
                max_single_duration=max_single_duration,
                leave_ratio=leave_ratio,
                behavior_tags=behavior_tags,
                stored_reasons=stored_risk_reasons,
                rapid_trips=rapid_trips,
                max_leave_density=max_leave_density,
            )
            
            # S8.4.2: 生成行为详情列表
            behavior_details = self._generate_behavior_details(events, behavior_tags)
            
            # S8.4.3-b: 生成审核建议
            review_suggestion = self._generate_review_suggestion(risk_level)

            return {
                "has_analysis": True,
                "exam_duration": exam_duration,
                "leave_ratio": leave_ratio,
                "max_single_duration": max_single_duration,
                "average_leave_duration": average_leave_duration,
                "risk_reason": risk_reason,
                "behavior_tags": behavior_tags,
                "behavior_details": behavior_details,
                "review_suggestion": review_suggestion,
            }

        except Exception as e:
            logger.error(
                "生成监考分析失败: record_id=%s, error=%s",
                exam_record.id if exam_record else "unknown",
                str(e),
            )
            return default_analysis

    @staticmethod
    def _calc_exam_duration(exam_record: ExamRecord) -> int:
        """计算考试总时长（秒）"""
        if not exam_record or not exam_record.started_at:
            return 0
        try:
            end_time = exam_record.submitted_at or datetime.now()
            duration = (end_time - exam_record.started_at).total_seconds()
            return max(int(duration), 0)
        except Exception:
            return 0

    @staticmethod
    def _calc_max_single_duration(events: list) -> int:
        """计算单次最长离开时长（秒）"""
        if not events:
            return 0
        max_duration_ms = 0
        for event in events:
            duration = event.get("duration", 0)
            if duration > max_duration_ms:
                max_duration_ms = duration
        return max_duration_ms // 1000

    @staticmethod
    def _calc_leave_ratio(total_duration: int, exam_duration: int) -> float:
        """计算离开时间占比（%）"""
        if exam_duration <= 0:
            return 0.0
        return round(total_duration / exam_duration * 100, 2)

    @staticmethod
    def _calc_average_leave_duration(total_duration: int, leave_count: int) -> float:
        """计算平均每次离开时长（秒）"""
        if leave_count <= 0:
            return 0.0
        return round(total_duration / leave_count, 2)

    @staticmethod
    def _generate_risk_reason(
        risk_level: str,
        leave_count: int,
        total_duration: int,
        max_single_duration: int,
        leave_ratio: float,
    ) -> str:
        """生成风险原因说明（V1 - 保持向后兼容）"""
        if leave_count == 0:
            return "考试过程中未检测到离开行为，考试状态正常"

        reasons = []

        # 基础信息
        reasons.append(f"离开{leave_count}次")
        reasons.append(f"累计离开{total_duration}秒")

        # 单次最长
        if max_single_duration > 0:
            reasons.append(f"单次最长离开{max_single_duration}秒")

        # 占比
        if leave_ratio > 0:
            reasons.append(f"离开时间占考试时长{leave_ratio:.1f}%")

        # 风险等级说明
        level_desc = {
            "normal": "风险等级：正常",
            "low": "风险等级：低风险",
            "medium": "风险等级：中风险",
            "high": "风险等级：高风险",
        }
        reasons.append(level_desc.get(risk_level, f"风险等级：{risk_level}"))

        # 建议
        if risk_level in ("high", "medium"):
            reasons.append("建议人工复核")

        return "，".join(reasons) + "。"

    @staticmethod
    def _generate_risk_reason_v2(
        risk_level: str,
        leave_count: int,
        total_duration: int,
        max_single_duration: int,
        leave_ratio: float,
        behavior_tags: list = None,
        stored_reasons: list = None,
        rapid_trips: int = 0,
        max_leave_density: float = 0.0,
    ) -> str:
        """S8.4.2: 生成增强版风险原因说明
        
        整合基础指标 + 行为标签 + 存储的详细原因
        """
        behavior_tags = behavior_tags or []
        stored_reasons = stored_reasons or []
        
        if leave_count == 0:
            return "考试过程中未检测到离开行为，考试状态正常"

        reasons = []

        # 基础信息
        reasons.append(f"考试期间共离开{leave_count}次")
        if total_duration > 0:
            reasons.append(f"累计离开时长{total_duration}秒")

        # S8.4.2: 存储的详细原因优先展示
        if stored_reasons:
            reasons.extend(stored_reasons)
        else:
            # 无存储原因时，根据指标生成
            if max_single_duration > 0:
                reasons.append(f"单次最长离开{max_single_duration}秒")
            if leave_ratio > 0:
                reasons.append(f"离开时间占考试时长{leave_ratio:.1f}%")

        # S8.4.2: 异常标签说明
        tag_desc_map = {
            'rapid_leave_return': '存在快速离开返回行为',
            'long_leave': '存在长时间离开',
            'frequent_leave': '离开行为集中',
            'network_related': '部分离开与网络异常相关',
            'refresh_attempt': '检测到页面刷新尝试',
        }
        for tag in behavior_tags:
            if tag in tag_desc_map and tag_desc_map[tag] not in stored_reasons:
                reasons.append(tag_desc_map[tag])

        # S8.4.2: 补充量化指标
        if rapid_trips > 0 and rapid_trips < 3:
            reasons.append(f"其中{rapid_trips}次为快速离开返回")
        
        if max_leave_density > 0.6:
            reasons.append(f"离开集中时段密度{max_leave_density}次/分钟")

        # 风险等级说明
        level_desc = {
            "normal": "风险等级：正常",
            "low": "风险等级：低风险",
            "medium": "风险等级：中风险",
            "high": "风险等级：高风险",
        }
        reasons.append(level_desc.get(risk_level, f"风险等级：{risk_level}"))

        # 建议
        if risk_level in ("high", "medium"):
            reasons.append("建议人工复核")

        return "，".join(reasons) + "。"

    @staticmethod
    def _generate_behavior_details(events: list, behavior_tags: list) -> list:
        """S8.4.2/S8.4.5: 生成行为详情列表供HR展示

        提取关键异常事件，生成可读的行为描述：
        - S8.4.2: 带标签的 exam_leave 事件
        - S8.4.5: 异常中断恢复 / 网络异常 / 设备方向变化 / 刷新尝试事件
        """
        if not events:
            return []

        behavior_tags = behavior_tags or []
        details = []

        def _fmt_time(ts):
            if not ts:
                return ''
            try:
                from datetime import datetime
                return datetime.fromtimestamp(ts / 1000).strftime('%H:%M:%S')
            except Exception:
                return str(ts)

        def _fmt_duration(duration_ms):
            return f"{duration_ms // 1000}秒" if duration_ms and duration_ms > 0 else ''

        # 找出带标签的 exam_leave 事件
        leave_events = [e for e in events if e.get('type') == 'exam_leave']

        for leave_event in leave_events:
            tags = leave_event.get('tags', [])
            if not tags:
                continue

            duration = leave_event.get('duration', 0)

            # 生成标签描述
            tag_labels = {
                'rapid_leave_return': '⚡ 快速返回',
                'long_leave': '⏱️ 长时间离开',
                'frequent_leave': '📊 高频离开',
                'network_related': '📡 网络相关',
                'recovered': '🔄 异常中断恢复',
            }

            tag_texts = [tag_labels.get(t, t) for t in tags]

            detail = {
                'time': _fmt_time(leave_event.get('timestamp', 0)),
                'duration': _fmt_duration(duration) or '进行中',
                'tags': tags,
                'tag_texts': tag_texts,
            }
            details.append(detail)

        # S8.4.5: 异常恢复 / 网络 / 方向 / 刷新事件的可读描述
        special_descriptions = {
            'leave_recovered': '检测到考试页面异常关闭后恢复',
            'network_offline': '检测到考试期间网络异常中断',
            'network_online': '检测到网络连接恢复',
            'orientation_change': '检测到设备方向变化',
            'refresh_attempt': '检测到页面刷新尝试',
        }

        for event in events:
            etype = event.get('type', '')
            if etype not in special_descriptions:
                continue

            duration = event.get('duration', 0)
            detail = {
                'time': _fmt_time(event.get('timestamp', 0)),
                'duration': _fmt_duration(duration) or '-',
                'tags': [etype],
                'tag_texts': [special_descriptions[etype]],
            }
            details.append(detail)

        # 按时间排序后限制数量
        details.sort(key=lambda x: x.get('time', ''))
        return details[-10:]  # 最多返回最近10条

    @staticmethod
    def _generate_review_suggestion(risk_level: str) -> str:
        """S8.4.3-b: 根据风险等级生成系统审核建议
        
        仅作为HR辅助参考，不参与评分，不影响最终成绩。
        明确排除判断性词语（如"作弊"、"违规"）。
        
        Args:
            risk_level: 风险等级 normal/low/medium/high
        
        Returns:
            str: 审核建议文案
        """
        suggestion_map = {
            'normal': '考试行为正常，无明显异常，可直接查看成绩',
            'low': '存在轻微异常行为，建议正常查看',
            'medium': '建议人工查看异常时间段答题情况',
            'high': '建议重点复核离开期间的答题内容',
        }
        return suggestion_map.get(risk_level, '')

    def update_hr_review(
        self,
        exam_record_id: int,
        review_score: float,
        review_comment: str | None = None,
    ) -> dict:
        """更新HR复核分数

        Args:
            exam_record_id: 考试记录 ID
            review_score: HR复核分数
            review_comment: HR复核备注

        Returns:
            dict: 更新后的评分记录数据
        """
        # 查询评分记录
        grading = self.get_grading_by_record_id(exam_record_id)
        if not grading:
            raise NotFoundException("评分记录不存在")

        if grading.status != "completed":
            raise BusinessException("评分尚未完成，无法进行HR复核")

        # 查询考试信息用于分数校验
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        exam = self.db.query(Exam).filter(Exam.id == exam_record.exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        # 计算试卷总分
        from app.models.question import Question
        questions = self.db.query(Question).filter(Question.exam_id == exam.id).all()
        max_total_score = sum(float(q.score) for q in questions)

        # 校验复核分数
        if review_score < 0:
            raise BusinessException("复核分数不能为负数")
        if review_score > max_total_score:
            raise BusinessException(f"复核分数不能超过试卷满分 {max_total_score}")

        # 更新复核字段
        grading.review_score = review_score
        grading.review_comment = review_comment
        self.db.commit()
        self.db.refresh(grading)

        logger.info(
            f"HR复核更新: exam_record_id={exam_record_id}, "
            f"review_score={review_score}, review_comment={review_comment}"
        )

        # 返回更新后的完整数据
        return self.get_grading_result_detail(exam_record_id)
