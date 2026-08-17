"""
考试服务
"""
import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.question import Question
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

    @staticmethod
    def _generate_exam_code() -> str:
        """生成唯一考试码"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = uuid.uuid4().hex[:8].upper()
        return f"EXAM-{timestamp}-{short_uuid}"

    def create_exam(self, title: str, duration_minutes: int, created_by: int, **kwargs) -> Exam:
        # 如果没有提供 exam_code，则自动生成
        if not kwargs.get("exam_code"):
            kwargs["exam_code"] = self._generate_exam_code()
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
        
        # 调整删除权限：允许 draft 和 closed 状态，禁止 published 状态
        if exam.status == "published":
            raise BusinessException("考试进行中，禁止删除。请先关闭考试。")
            
        if exam.status not in ["draft", "closed"]:
            raise BusinessException("当前试卷状态不允许删除")
            
        # 增加删除安全校验：检查 closed 状态试卷是否存在历史考试数据
        if exam.status == "closed":
            # 检查是否存在考试记录
            if exam.exam_records and len(exam.exam_records) > 0:
                raise BusinessException(
                    "该试卷已有历史考试记录，删除后可能影响成绩查看，请确认"
                )

        return self.delete(exam_id)

    def publish_exam(self, exam_id: int, current_user: User) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "操作")
        if exam.status not in ["draft", "closed"]:
            raise BusinessException("只有草稿或已关闭的考试才能发布")
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

    def clone_exam(self, exam_id: int, current_user: User, new_title: str = None) -> Exam:
        """复制考试为新实例（用于试卷复用）

        Args:
            exam_id: 原考试ID
            current_user: 当前用户
            new_title: 新考试标题（可选，默认在原标题后加"（副本）"）

        Returns:
            新的 Exam 实例
        """
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        self._ensure_owner_or_admin(exam, current_user, "复制")

        # 创建新的 Exam 实例
        new_exam = Exam(
            title=new_title or f"{exam.title}（副本）",
            exam_code=self._generate_exam_code(),
            position=exam.position,
            description=exam.description,
            duration_minutes=exam.duration_minutes,
            pass_score=exam.pass_score,
            status="draft",
            created_by=current_user.id,
        )
        self.db.add(new_exam)
        self.db.flush()  # 获取新 ID

        # 复制题目
        for question in exam.questions:
            new_question = Question(
                exam_id=new_exam.id,
                type=question.type,
                content=question.content,
                question_no=question.question_no,
                category=question.category,
                options=question.options,
                answer=question.answer,
                score=question.score,
                sort_order=question.sort_order,
            )
            self.db.add(new_question)

        self.db.commit()
        self.db.refresh(new_exam)
        return new_exam

    def get_exam_detail(self, exam_id: int) -> Exam:
        exam = self.get(exam_id)
        if not exam:
            raise NotFoundException("考试不存在")
        return exam

    def get_by_code(self, exam_code: str) -> Exam | None:
        """通过考试码查找考试"""
        return self.db.query(Exam).filter(Exam.exam_code == exam_code).first()

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
