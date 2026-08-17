"""
题目服务
"""
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.question import Question
from app.models.user import User
from app.services.base import BaseService


class QuestionService(BaseService[Question]):
    def __init__(self, db: Session):
        super().__init__(db, Question)

    @staticmethod
    def _ensure_owner_or_admin(exam: Exam, current_user: User, action: str = "操作") -> None:
        if current_user.role == "admin":
            return
        if exam.created_by != current_user.id:
            raise BusinessException(f"无权{action}此考试")

    def get_by_exam(self, exam_id: int) -> list[Question]:
        return (
            self.db.query(Question)
            .filter(Question.exam_id == exam_id)
            .order_by(Question.sort_order)
            .all()
        )

    def create_question(self, exam_id: int, current_user: User, **kwargs) -> Question:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能添加题目")
        self._validate_question_data(kwargs)
        return self.create(exam_id=exam_id, **kwargs)

    def update_question(self, exam_id: int, question_id: int, current_user: User, **kwargs) -> Question:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能修改题目")
        question = self.get(question_id)
        if not question or question.exam_id != exam_id:
            raise NotFoundException("题目不存在")
        self._validate_question_data(kwargs)
        return self.update(question_id, **kwargs)

    def delete_question(self, exam_id: int, question_id: int, current_user: User) -> bool:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能删除题目")
        question = self.get(question_id)
        if not question or question.exam_id != exam_id:
            raise NotFoundException("题目不存在")

        deleted_sort_order = question.sort_order
        result = self.delete(question_id)

        remaining = (
            self.db.query(Question)
            .filter(Question.exam_id == exam_id)
            .order_by(Question.sort_order)
            .all()
        )
        for i, q in enumerate(remaining):
            new_order = i
            if q.sort_order != new_order:
                q.sort_order = new_order
        self.db.commit()

        return result

    def batch_create(self, exam_id: int, current_user: User, questions: list[dict]) -> list[Question]:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能添加题目")
        created = []
        for q in questions:
            self._validate_question_data(q)
            obj = self.create(exam_id=exam_id, **q)
            created.append(obj)
        return created

    def delete_by_exam(self, exam_id: int, current_user: User) -> None:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能清空题目")
        self.db.query(Question).filter(Question.exam_id == exam_id).delete()
        self.db.commit()

    def _validate_question_data(self, data: dict) -> None:
        q_type = data.get("type")
        options = data.get("options")
        answer = data.get("answer")

        if q_type in ("single_choice", "multiple_choice"):
            if options is not None and len(options) < 2:
                raise BusinessException(f"{q_type} 题型至少需要 2 个选项")
            if answer is not None and not answer.strip():
                raise BusinessException("答案不能为空")
        elif q_type == "true_false":
            if answer is not None and answer not in ("true", "false"):
                raise BusinessException("判断题答案必须是 'true' 或 'false'")
        elif q_type == "short_answer":
            if answer is not None and not answer.strip():
                raise BusinessException("简答题答案不能为空")
