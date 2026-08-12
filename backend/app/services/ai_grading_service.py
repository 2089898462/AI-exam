"""
AI 阅卷服务 (AIGradingService)

负责调用 AI-Service 执行简答题评分。

调用链：
Exam 业务 → AIGradingService → AIScoringService → AI-Service → DeepSeek-V4-Flash

职责：
- 构造评分请求（不包含候选人隐私信息）
- 调用 AI 评分服务
- 解析并标准化 AI 评分结果
- 保存评分结果到 AIScoreRecord 和 AnswerRecord
- 管理 AI 评分状态（触发/查询/确认/拒绝）
- 异常处理（不影响考试提交）

安全：
- 发送给 AI 的数据只包含题目、标准答案、评分规则、候选答案
- 禁止发送候选人隐私信息（姓名、手机号、邮箱、身份证等）
"""
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.answer_record import AnswerRecord
from app.models.ai_score_record import AIScoreRecord
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.services.ai_scoring_service import ai_scoring_service

logger = get_logger(__name__)


class AIGradingService:
    """AI 阅卷服务

    独立封装 AI 评分逻辑，业务接口不直接调用 AI 服务。
    """

    # AI 评分状态流转
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    def __init__(self, db: Session):
        self.db = db

    def trigger_ai_scoring(
        self,
        answer_record_id: int,
    ) -> AIScoreRecord:
        """触发 AI 评分

        对指定答题记录执行 AI 评分，生成评分建议。
        AI 只提供建议，不直接修改成绩。

        Args:
            answer_record_id: 答题记录 ID

        Returns:
            AIScoreRecord: AI 评分记录

        Raises:
            NotFoundException: 答题记录不存在
            BusinessException: 非简答题类型 / 已存在评分记录
        """
        # 1. 加载答题记录和题目信息
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if not answer_record:
            raise NotFoundException("答题记录不存在")

        question = self.db.query(Question).filter(
            Question.id == answer_record.question_id
        ).first()
        if not question:
            raise NotFoundException("题目不存在")

        # 2. 验证题型
        if question.type != "short_answer":
            raise BusinessException(f"题型为 {question.type}，仅支持简答题 AI 评分")

        # 3. 检查是否已存在评分记录
        existing = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id == answer_record_id,
        ).order_by(AIScoreRecord.id.desc()).first()

        if existing:
            if existing.review_status == "rejected":
                # 被拒绝的可以重新触发，更新原记录
                return self._regenerate_ai_scoring(existing, answer_record, question)
            elif existing.review_status not in ("completed",):
                raise BusinessException("已存在 AI 评分记录，请查询结果或等待确认")

        # 4. 执行 AI 评分
        result = self._execute_ai_scoring(answer_record, question)

        # 5. 创建评分记录
        ai_score_record = self._create_ai_score_record(answer_record, question, result)

        logger.info(
            f"AI 评分完成: answer_record_id={answer_record_id}, "
            f"score={result['score']}, confidence={result.get('confidence', 0)}"
        )

        return ai_score_record

    def get_ai_scoring_result(
        self,
        answer_record_id: int,
    ) -> dict[str, Any]:
        """查询 AI 评分结果

        Args:
            answer_record_id: 答题记录 ID

        Returns:
            dict: 评分结果详情
        """
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if not answer_record:
            raise NotFoundException("答题记录不存在")

        question = self.db.query(Question).filter(
            Question.id == answer_record.question_id
        ).first()
        if not question:
            raise NotFoundException("题目不存在")

        ai_score_record = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id == answer_record_id
        ).order_by(AIScoreRecord.id.desc()).first()

        if not ai_score_record:
            raise BusinessException("尚无 AI 评分记录，请先触发评分")

        # 解析 JSON 字段
        matched_points = json.loads(ai_score_record.matched_points) if ai_score_record.matched_points else []
        missing_points = json.loads(ai_score_record.missing_points) if ai_score_record.missing_points else []

        return {
            "answer_record_id": answer_record_id,
            "question_id": answer_record.question_id,
            "question_content": question.content,
            "candidate_answer": answer_record.answer_content,
            "ai_score": float(ai_score_record.ai_score),
            "max_score": float(ai_score_record.max_score),
            "score_reason": ai_score_record.score_reason,
            "matched_points": matched_points,
            "missing_points": missing_points,
            "confidence": float(ai_score_record.confidence),
            "needs_review": answer_record.needs_review,
            "review_status": ai_score_record.review_status,
            "confirmed_score": float(ai_score_record.confirmed_score) if ai_score_record.confirmed_score else None,
            "hr_remark": ai_score_record.hr_remark,
            "model_name": ai_score_record.model_name,
            "prompt_version": ai_score_record.prompt_version,
            "created_at": ai_score_record.created_at.isoformat() if ai_score_record.created_at else None,
        }

    def confirm_ai_scoring(
        self,
        answer_record_id: int,
        confirmed_score: float,
        reviewer_id: int,
        hr_remark: str | None = None,
    ) -> AIScoreRecord:
        """HR 确认 AI 评分

        确认后：
        1. AI 评分记录状态变为 completed
        2. 答题记录的 score 更新为确认分数
        3. 不可再修改

        Args:
            answer_record_id: 答题记录 ID
            confirmed_score: HR 确认的最终分数
            reviewer_id: 审核人 ID
            hr_remark: HR 备注

        Returns:
            AIScoreRecord: 更新后的评分记录
        """
        ai_score_record = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id == answer_record_id
        ).order_by(AIScoreRecord.id.desc()).first()

        if not ai_score_record:
            raise BusinessException("AI 评分记录不存在，无法确认")

        if ai_score_record.review_status not in ("ai_scored", "hr_confirmed"):
            raise BusinessException(f"当前状态为 {ai_score_record.review_status}，无法确认")

        # 验证分数范围
        if confirmed_score < 0 or confirmed_score > float(ai_score_record.max_score):
            raise BusinessException(
                f"确认分数必须在 0 ~ {float(ai_score_record.max_score)} 范围内"
            )

        # 更新评分记录
        ai_score_record.review_status = "completed"
        ai_score_record.reviewed_by = reviewer_id
        ai_score_record.reviewed_at = datetime.now()
        ai_score_record.hr_remark = hr_remark
        ai_score_record.confirmed_score = confirmed_score

        # 更新答题记录
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if answer_record:
            answer_record.score = confirmed_score
            answer_record.is_correct = confirmed_score > 0

        self.db.commit()
        self.db.refresh(ai_score_record)

        logger.info(
            f"HR 确认 AI 评分: answer_record_id={answer_record_id}, "
            f"confirmed_score={confirmed_score}, reviewer_id={reviewer_id}"
        )

        return ai_score_record

    def reject_ai_scoring(
        self,
        answer_record_id: int,
        reviewer_id: int,
        hr_remark: str | None = None,
    ) -> AIScoreRecord:
        """HR 拒绝 AI 评分

        拒绝后：
        1. AI 评分记录状态变为 rejected
        2. 可重新触发 AI 评分

        Args:
            answer_record_id: 答题记录 ID
            reviewer_id: 审核人 ID
            hr_remark: 拒绝原因

        Returns:
            AIScoreRecord: 更新后的评分记录
        """
        ai_score_record = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id == answer_record_id
        ).order_by(AIScoreRecord.id.desc()).first()

        if not ai_score_record:
            raise BusinessException("AI 评分记录不存在，无法拒绝")

        if ai_score_record.review_status == "completed":
            raise BusinessException("评分已确认，无法拒绝")

        # 更新评分记录
        ai_score_record.review_status = "rejected"
        ai_score_record.reviewed_by = reviewer_id
        ai_score_record.reviewed_at = datetime.now()
        ai_score_record.hr_remark = hr_remark

        self.db.commit()
        self.db.refresh(ai_score_record)

        logger.info(
            f"HR 拒绝 AI 评分: answer_record_id={answer_record_id}, "
            f"reviewer_id={reviewer_id}, remark={hr_remark}"
        )

        return ai_score_record

    def get_ai_scoring_status(
        self,
        answer_record_id: int,
    ) -> dict[str, Any]:
        """获取 AI 评分状态

        Args:
            answer_record_id: 答题记录 ID

        Returns:
            dict: 评分状态信息
        """
        answer_record = self.db.query(AnswerRecord).filter(
            AnswerRecord.id == answer_record_id
        ).first()
        if not answer_record:
            raise NotFoundException("答题记录不存在")

        ai_score_record = self.db.query(AIScoreRecord).filter(
            AIScoreRecord.answer_record_id == answer_record_id
        ).order_by(AIScoreRecord.id.desc()).first()

        if not ai_score_record:
            return {
                "answer_record_id": answer_record_id,
                "has_ai_score": False,
                "review_status": None,
                "ai_score": None,
                "confirmed_score": None,
                "message": "尚无 AI 评分记录",
            }

        return {
            "answer_record_id": answer_record_id,
            "has_ai_score": True,
            "review_status": ai_score_record.review_status,
            "ai_score": float(ai_score_record.ai_score),
            "confirmed_score": float(ai_score_record.confirmed_score) if ai_score_record.confirmed_score else None,
            "message": f"AI 评分状态: {ai_score_record.review_status}",
        }

    def get_pending_ai_scores(
        self,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ) -> dict[str, Any]:
        """获取待审核 AI 评分列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选

        Returns:
            dict: {items: list, total: int, page: int, page_size: int}
        """
        query = self.db.query(AIScoreRecord)

        # 默认显示非 completed 的记录
        if status:
            query = query.filter(AIScoreRecord.review_status == status)
        else:
            query = query.filter(
                AIScoreRecord.review_status.in_(["ai_scored", "hr_confirmed", "rejected"])
            )

        total = query.count()
        records = query.order_by(AIScoreRecord.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        items = []
        for record in records:
            answer_record = self.db.query(AnswerRecord).filter(
                AnswerRecord.id == record.answer_record_id
            ).first()
            question = self.db.query(Question).filter(
                Question.id == answer_record.question_id if answer_record else 0
            ).first()

            matched_points = json.loads(record.matched_points) if record.matched_points else []
            missing_points = json.loads(record.missing_points) if record.missing_points else []

            items.append({
                "id": record.id,
                "answer_record_id": record.answer_record_id,
                "question_id": answer_record.question_id if answer_record else None,
                "question_content": question.content if question else "",
                "candidate_answer": answer_record.answer_content if answer_record else None,
                "ai_score": float(record.ai_score),
                "max_score": float(record.max_score),
                "score_reason": record.score_reason,
                "matched_points": matched_points,
                "missing_points": missing_points,
                "confidence": float(record.confidence),
                "needs_review": answer_record.needs_review if answer_record else False,
                "review_status": record.review_status,
                "confirmed_score": float(record.confirmed_score) if record.confirmed_score else None,
                "model_name": record.model_name,
                "prompt_version": record.prompt_version,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def grade_short_answer(
        self,
        answer_record_id: int,
    ) -> dict[str, Any]:
        """对单道简答题执行 AI 评分（兼容旧接口）

        Args:
            answer_record_id: 答题记录 ID

        Returns:
            dict: 评分结果
        """
        ai_score_record = self.trigger_ai_scoring(answer_record_id)
        return {
            "score": float(ai_score_record.ai_score),
            "reason": ai_score_record.score_reason,
            "matched_points": json.loads(ai_score_record.matched_points) if ai_score_record.matched_points else [],
            "missing_points": json.loads(ai_score_record.missing_points) if ai_score_record.missing_points else [],
            "confidence": float(ai_score_record.confidence),
            "needs_review": True,
            "ai_status": self.STATUS_COMPLETED,
        }

    def grade_exam_short_answers(
        self,
        exam_record_id: int,
    ) -> dict[str, Any]:
        """对考试中的所有简答题执行 AI 评分

        Args:
            exam_record_id: 考试记录 ID

        Returns:
            dict: 评分汇总结果
        """
        exam_record = self.db.query(ExamRecord).filter(
            ExamRecord.id == exam_record_id
        ).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        answer_records = self.db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == exam_record_id
        ).all()

        short_answer_records = []
        for ar in answer_records:
            question = self.db.query(Question).filter(
                Question.id == ar.question_id
            ).first()
            if question and question.type == "short_answer":
                short_answer_records.append(ar)

        if not short_answer_records:
            return {
                "total_short_answers": 0,
                "graded_count": 0,
                "failed_count": 0,
                "results": [],
            }

        results = []
        failed_count = 0
        for ar in short_answer_records:
            try:
                ai_record = self.trigger_ai_scoring(ar.id)
                results.append({
                    "answer_record_id": ar.id,
                    "question_id": ar.question_id,
                    "score": float(ai_record.ai_score),
                    "ai_status": ai_record.review_status,
                })
            except Exception as e:
                failed_count += 1
                results.append({
                    "answer_record_id": ar.id,
                    "question_id": ar.question_id,
                    "score": 0,
                    "ai_status": self.STATUS_FAILED,
                    "error": str(e),
                })

        return {
            "total_short_answers": len(short_answer_records),
            "graded_count": len(short_answer_records) - failed_count,
            "failed_count": failed_count,
            "results": results,
        }

    def _execute_ai_scoring(
        self,
        answer_record: AnswerRecord,
        question: Question,
    ) -> dict[str, Any]:
        """执行 AI 评分（内部方法）

        Args:
            answer_record: 答题记录
            question: 题目

        Returns:
            dict: AI 评分结果
        """
        # 处理空答案
        candidate_answer = answer_record.answer_content or ""
        if not candidate_answer.strip():
            return {
                "score": 0.0,
                "reason": "候选人未作答",
                "matched_points": [],
                "missing_points": ["全部要点"],
                "confidence": 1.0,
                "needs_review": False,
                "prompt_version": "v2",
                "is_empty_answer": True,
            }

        # 调用 AI 评分服务
        try:
            result = ai_scoring_service.evaluate_scoring(
                question=question.content,
                standard_answer=question.answer or "",
                user_answer=candidate_answer,
                max_score=float(question.score),
                scoring_rules=None,
                prompt_version="v2",
            )
            return result

        except BusinessException as e:
            logger.error(f"AI 评分服务调用失败: {str(e)}")
            return {
                "score": 0.0,
                "reason": f"AI 评分服务异常: {str(e)}",
                "matched_points": [],
                "missing_points": [],
                "confidence": 0.0,
                "needs_review": True,
                "prompt_version": "v2",
                "is_empty_answer": False,
                "is_error": True,
            }
        except Exception as e:
            logger.error(f"AI 评分异常: {str(e)}")
            return {
                "score": 0.0,
                "reason": f"AI 评分异常: {str(e)}",
                "matched_points": [],
                "missing_points": [],
                "confidence": 0.0,
                "needs_review": True,
                "prompt_version": "v2",
                "is_empty_answer": False,
                "is_error": True,
            }

    def _create_ai_score_record(
        self,
        answer_record: AnswerRecord,
        question: Question,
        result: dict[str, Any],
    ) -> AIScoreRecord:
        """创建 AI 评分记录

        Args:
            answer_record: 答题记录
            question: 题目
            result: AI 评分结果

        Returns:
            AIScoreRecord: 创建的评分记录
        """
        matched_points = result.get("matched_points", [])
        missing_points = result.get("missing_points", [])
        score = float(result.get("score", 0))
        confidence = float(result.get("confidence", 0))
        needs_review = result.get("needs_review", False)

        # 构建评分理由
        enhanced_reason = result.get("reason", "")
        if matched_points:
            enhanced_reason += f"\n\n覆盖知识点: {', '.join(matched_points)}"
        if missing_points:
            enhanced_reason += f"\n\n遗漏要点: {', '.join(missing_points)}"

        # 创建 AIScoreRecord
        ai_score_record = AIScoreRecord(
            answer_record_id=answer_record.id,
            ai_score=score,
            max_score=float(question.score),
            score_reason=enhanced_reason,
            matched_points=json.dumps(matched_points, ensure_ascii=False),
            missing_points=json.dumps(missing_points, ensure_ascii=False),
            confidence=confidence,
            model_name="deepseek-chat",
            prompt_version=result.get("prompt_version", "v2"),
            review_status="ai_scored",
        )
        self.db.add(ai_score_record)

        # 更新答题记录的 AI 相关字段
        answer_record.ai_score = score
        answer_record.ai_reason = enhanced_reason
        answer_record.ai_comment = enhanced_reason
        answer_record.ai_confidence = confidence
        answer_record.needs_review = needs_review
        answer_record.prompt_version = result.get("prompt_version", "v2")
        answer_record.ai_model_used = "deepseek-v4-flash"
        answer_record.ai_scored_at = datetime.now()
        answer_record.matched_points = matched_points
        answer_record.missing_points = missing_points
        answer_record.knowledge_points = {
            "matched": matched_points,
            "missing": missing_points,
        }

        if result.get("is_error"):
            answer_record.ai_status = self.STATUS_FAILED
            answer_record.ai_error_message = result.get("reason", "")
        else:
            answer_record.ai_status = self.STATUS_COMPLETED
            answer_record.ai_error_message = None

        # 空答案：保留 ai_scored 状态，由 HR 确认
        if result.get("is_empty_answer"):
            ai_score_record.review_status = "ai_scored"
            ai_score_record.confidence = 1.0
            ai_score_record.score_reason = "候选人未作答，AI 建议 0 分"
            answer_record.score = 0.0
            answer_record.is_correct = False
            answer_record.ai_confidence = 1.0
            answer_record.needs_review = False

        self.db.commit()
        self.db.refresh(ai_score_record)
        return ai_score_record

    def _regenerate_ai_scoring(
        self,
        existing_record: AIScoreRecord,
        answer_record: AnswerRecord,
        question: Question,
    ) -> AIScoreRecord:
        """重新生成 AI 评分（被拒绝后）

        Args:
            existing_record: 已有的评分记录
            answer_record: 答题记录
            question: 题目

        Returns:
            AIScoreRecord: 更新后的评分记录
        """
        # 执行新的 AI 评分
        result = self._execute_ai_scoring(answer_record, question)

        matched_points = result.get("matched_points", [])
        missing_points = result.get("missing_points", [])
        score = float(result.get("score", 0))
        confidence = float(result.get("confidence", 0))

        # 构建评分理由
        enhanced_reason = result.get("reason", "")
        if matched_points:
            enhanced_reason += f"\n\n覆盖知识点: {', '.join(matched_points)}"
        if missing_points:
            enhanced_reason += f"\n\n遗漏要点: {', '.join(missing_points)}"

        # 更新已有记录
        existing_record.ai_score = score
        existing_record.max_score = float(question.score)
        existing_record.score_reason = enhanced_reason
        existing_record.matched_points = json.dumps(matched_points, ensure_ascii=False)
        existing_record.missing_points = json.dumps(missing_points, ensure_ascii=False)
        existing_record.confidence = confidence
        existing_record.model_name = "deepseek-v4-flash"
        existing_record.prompt_version = result.get("prompt_version", "v2")
        existing_record.review_status = "ai_scored"
        existing_record.reviewed_by = None
        existing_record.reviewed_at = None
        existing_record.hr_remark = None
        existing_record.confirmed_score = None

        # 更新答题记录
        answer_record.ai_score = score
        answer_record.ai_reason = enhanced_reason
        answer_record.ai_comment = enhanced_reason
        answer_record.ai_confidence = confidence
        answer_record.needs_review = result.get("needs_review", False)
        answer_record.prompt_version = result.get("prompt_version", "v2")
        answer_record.matched_points = matched_points
        answer_record.missing_points = missing_points
        answer_record.knowledge_points = {
            "matched": matched_points,
            "missing": missing_points,
        }

        self.db.commit()
        self.db.refresh(existing_record)
        return existing_record


def get_ai_grading_service(db: Session) -> AIGradingService:
    """获取 AI 阅卷服务实例"""
    return AIGradingService(db=db)
