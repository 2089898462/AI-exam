"""
考试服务
"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.user import User
from app.services.base import BaseService


class ExamService(BaseService[Exam]):
    def __init__(self, db: Session):
        super().__init__(db, Exam)

    @staticmethod
    def _ensure_owner_or_admin(exam: Exam, current_user: User, action: str = "操作") -> None:
        if current_user.role == "admin":
            return
        if exam.created_by != current_user.id:
            raise BusinessException(f"无权{action}此考试")

    def create_exam(self, title: str, duration_minutes: int, created_by: int, **kwargs) -> Exam:
        return self.create(
            title=title,
            duration_minutes=duration_minutes,
            created_by=created_by,
            **kwargs,
        )

    def update_exam(self, exam_id: int, current_user: User, **kwargs) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "修改")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能修改")
        return self.update(exam_id, **kwargs)

    def delete_exam(self, exam_id: int, current_user: User) -> bool:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "删除")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能删除")
        return self.delete(exam_id)

    def publish_exam(self, exam_id: int, current_user: User) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能发布")
        if not exam.questions:
            raise BusinessException("考试至少需要一道题目才能发布")
        exam.status = "published"
        exam.published_at = datetime.now()
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def close_exam(self, exam_id: int, current_user: User) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status != "published":
            raise BusinessException("只有已发布的考试才能关闭")
        exam.status = "closed"
        exam.closed_at = datetime.now()
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def get_exam_detail(self, exam_id: int) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        return exam

    def list_exams(
        self,
        current_user: User,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Exam], int]:
        query = self.db.query(Exam)
        if current_user.role != "admin":
            query = query.filter(Exam.created_by == current_user.id)
        if status:
            query = query.filter(Exam.status == status)
        if keyword:
            filters = [Exam.title.contains(keyword)]
            query = query.filter(or_(*filters))
        total = query.count()
        items = query.order_by(Exam.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def count_questions(self, exam_id: int) -> int:
        exam = self.get(exam_id)
        if not exam:
            return 0
        return len(exam.questions)
