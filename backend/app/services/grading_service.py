"""
评分记录Service
管理考试评分记录的创建、状态流转和查询
支持客观题自动评分 + 主观题 AI 评分混合流程
"""
import asyncio
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.answer_record import AnswerRecord
from app.models.exam import Exam
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
        items = []
        for record in records:
            exam_record = self.db.query(ExamRecord).filter(
                ExamRecord.id == record.exam_record_id
            ).first()
            if exam_record:
                review_val = float(record.review_score) if record.review_score is not None else None
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
        }
        return result

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
