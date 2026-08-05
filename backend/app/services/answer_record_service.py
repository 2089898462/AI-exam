"""
答题记录Service
管理候选人答题记录的保存、查询
"""
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.answer_record import AnswerRecord
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.services.base import BaseService


# 允许答题的考试记录状态
_ANSWERABLE_STATUSES = {"not_started", "in_progress"}


class AnswerRecordService(BaseService[AnswerRecord]):
    """答题记录业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, AnswerRecord)

    def save_answer(
        self,
        record_id: int,
        question_id: int,
        answer_content: str | None,
    ) -> AnswerRecord:
        """保存单题答案

        校验：
        - 考试记录必须存在
        - 题目必须存在且属于该考试
        - 考试状态必须允许答题（not_started / in_progress）
        - 同一题目在同一考试记录中只能有一条答案（幂等更新）

        事务：失败自动回滚
        """
        exam_record = self.db.query(ExamRecord).filter(ExamRecord.id == record_id).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise NotFoundException("题目不存在")

        if question.exam_id != exam_record.exam_id:
            raise ValidationException("题目不属于该考试")

        if exam_record.status not in _ANSWERABLE_STATUSES:
            raise BusinessException(
                f"考试已{exam_record.status}，无法修改答案"
            )

        try:
            existing = (
                self.db.query(AnswerRecord)
                .filter(
                    AnswerRecord.exam_record_id == record_id,
                    AnswerRecord.question_id == question_id,
                )
                .first()
            )

            if existing:
                existing.answer_content = answer_content
                self.db.commit()
                self.db.refresh(existing)
                return existing

            answer = AnswerRecord(
                exam_record_id=record_id,
                question_id=question_id,
                answer_content=answer_content,
            )
            self.db.add(answer)
            self.db.commit()
            self.db.refresh(answer)
            return answer
        except Exception:
            self.db.rollback()
            raise

    def save_answers_batch(
        self,
        record_id: int,
        answers: list[dict],
    ) -> list[AnswerRecord]:
        """批量保存答案

        校验：
        - 考试记录必须存在且允许答题
        - 每个答案项必须包含 question_id
        - 批量操作保证事务一致性

        参数格式：
            answers = [
                {"question_id": 1, "answer_content": "A"},
                {"question_id": 2, "answer_content": "B"},
            ]
        """
        exam_record = self.db.query(ExamRecord).filter(ExamRecord.id == record_id).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        if exam_record.status not in _ANSWERABLE_STATUSES:
            raise BusinessException(
                f"考试已{exam_record.status}，无法提交答案"
            )

        if not answers:
            raise ValidationException("答案列表不能为空")

        saved = []
        try:
            for item in answers:
                question_id = item.get("question_id")
                if not question_id:
                    raise ValidationException("答案项缺少 question_id")

                answer_content = item.get("answer_content")

                question = self.db.query(Question).filter(Question.id == question_id).first()
                if not question:
                    raise NotFoundException(f"题目 {question_id} 不存在")
                if question.exam_id != exam_record.exam_id:
                    raise ValidationException(f"题目 {question_id} 不属于该考试")

                existing = (
                    self.db.query(AnswerRecord)
                    .filter(
                        AnswerRecord.exam_record_id == record_id,
                        AnswerRecord.question_id == question_id,
                    )
                    .first()
                )

                if existing:
                    existing.answer_content = answer_content
                    saved.append(existing)
                else:
                    answer = AnswerRecord(
                        exam_record_id=record_id,
                        question_id=question_id,
                        answer_content=answer_content,
                    )
                    self.db.add(answer)
                    saved.append(answer)

            self.db.commit()
            for a in saved:
                self.db.refresh(a)
            return saved
        except Exception:
            self.db.rollback()
            raise

    def get_answers_by_record(self, record_id: int) -> list[AnswerRecord]:
        """查询某考试记录的所有答题"""
        exam_record = self.db.query(ExamRecord).filter(ExamRecord.id == record_id).first()
        if not exam_record:
            raise NotFoundException("考试记录不存在")

        return (
            self.db.query(AnswerRecord)
            .filter(AnswerRecord.exam_record_id == record_id)
            .order_by(AnswerRecord.question_id.asc())
            .all()
        )
