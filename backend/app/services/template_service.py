"""
试卷模板服务
提供模板 CRUD、题目管理和基于模板创建考试功能
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.exam_template import ExamTemplate
from app.models.question import Question
from app.models.template_question import TemplateQuestion
from app.models.user import User
from app.services.base import BaseService


class TemplateService(BaseService[ExamTemplate]):
    def __init__(self, db: Session):
        super().__init__(db, ExamTemplate)

    @staticmethod
    def _ensure_owner_or_admin(template: ExamTemplate, current_user: User, action: str = "操作") -> None:
        if current_user.role == "admin":
            return
        if template.created_by != current_user.id:
            raise BusinessException(f"无权{action}此模板")

    def create_template(self, name: str, created_by: int, **kwargs) -> ExamTemplate:
        return self.create(
            name=name,
            created_by=created_by,
            **kwargs,
        )

    def update_template(self, template_id: int, current_user: User, **kwargs) -> ExamTemplate:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "修改")
        return self.update(template_id, **kwargs)

    def delete_template(self, template_id: int, current_user: User) -> bool:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "删除")
        return self.delete(template_id)

    def get_template_detail(self, template_id: int, current_user: User) -> ExamTemplate:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "查看")
        return template

    def list_templates(
        self,
        current_user: User,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExamTemplate], int]:
        query = self.db.query(ExamTemplate)
        if current_user.role != "admin":
            query = query.filter(ExamTemplate.created_by == current_user.id)
        if status:
            query = query.filter(ExamTemplate.status == status)
        if keyword:
            from sqlalchemy import or_
            filters = [ExamTemplate.name.contains(keyword)]
            query = query.filter(or_(*filters))
        total = query.count()
        items = query.order_by(ExamTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def activate_template(self, template_id: int, current_user: User) -> ExamTemplate:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        template.status = "active"
        self.db.commit()
        self.db.refresh(template)
        return template

    def deactivate_template(self, template_id: int, current_user: User) -> ExamTemplate:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        template.status = "inactive"
        self.db.commit()
        self.db.refresh(template)
        return template

    # ==================== 模板题目管理 ====================

    def get_template_questions(self, template_id: int) -> list[TemplateQuestion]:
        return (
            self.db.query(TemplateQuestion)
            .filter(TemplateQuestion.template_id == template_id)
            .order_by(TemplateQuestion.sort_order)
            .all()
        )

    def create_template_question(
        self, template_id: int, current_user: User, **kwargs
    ) -> TemplateQuestion:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        self._validate_question_data(kwargs)
        question = TemplateQuestion(template_id=template_id, **kwargs)
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def batch_create_questions(
        self, template_id: int, current_user: User, questions: list[dict]
    ) -> list[TemplateQuestion]:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        
        created = []
        for q in questions:
            self._validate_question_data(q)
            obj = TemplateQuestion(template_id=template_id, **q)
            self.db.add(obj)
            created.append(obj)
        self.db.commit()
        for obj in created:
            self.db.refresh(obj)
        return created

    def update_template_question(
        self, template_id: int, question_id: int, current_user: User, **kwargs
    ) -> TemplateQuestion:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        
        question = (
            self.db.query(TemplateQuestion)
            .filter(TemplateQuestion.id == question_id, TemplateQuestion.template_id == template_id)
            .first()
        )
        if not question:
            raise NotFoundException("模板题目不存在")
        
        if "type" in kwargs or "options" in kwargs or "answer" in kwargs:
            self._validate_question_data({
                "type": kwargs.get("type", question.type),
                "options": kwargs.get("options", question.options),
                "answer": kwargs.get("answer", question.answer),
            })
        
        for key, value in kwargs.items():
            if value is not None and hasattr(question, key):
                setattr(question, key, value)
        
        self.db.commit()
        self.db.refresh(question)
        return question

    def delete_template_question(
        self, template_id: int, question_id: int, current_user: User
    ) -> bool:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        
        question = (
            self.db.query(TemplateQuestion)
            .filter(TemplateQuestion.id == question_id, TemplateQuestion.template_id == template_id)
            .first()
        )
        if not question:
            raise NotFoundException("模板题目不存在")
        
        self.db.delete(question)
        self.db.commit()
        return True

    def delete_all_questions(self, template_id: int, current_user: User) -> None:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        self.db.query(TemplateQuestion).filter(TemplateQuestion.template_id == template_id).delete()
        self.db.commit()

    def count_questions(self, template_id: int) -> int:
        return (
            self.db.query(TemplateQuestion)
            .filter(TemplateQuestion.template_id == template_id)
            .count()
        )

    # ==================== 基于模板创建考试 ====================

    def create_exam_from_template(
        self,
        template_id: int,
        current_user: User,
        title: str | None = None,
        **exam_kwargs,
    ) -> Exam:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        
        questions = self.get_template_questions(template_id)
        if not questions:
            raise BusinessException("模板中没有题目，无法创建考试")
        
        # 创建考试实例
        exam_title = title or f"{template.name} - {datetime.now().strftime('%Y%m%d%H%M%S')}"
        duration_minutes = exam_kwargs.pop("duration_minutes", 60)
        pass_score = exam_kwargs.pop("pass_score", 60)
        
        exam = Exam(
            title=exam_title,
            exam_code=exam_kwargs.pop("exam_code", None),
            position=exam_kwargs.pop("position", None),
            description=exam_kwargs.pop("description", template.description),
            duration_minutes=duration_minutes,
            pass_score=pass_score,
            status="draft",
            created_by=current_user.id,
        )
        self.db.add(exam)
        self.db.flush()
        
        # 复制题目到考试
        for idx, tq in enumerate(questions):
            question = Question(
                exam_id=exam.id,
                question_no=tq.question_no,
                category=tq.category,
                type=tq.type,
                content=tq.content,
                options=tq.options,
                answer=tq.answer,
                score=tq.score,
                sort_order=tq.sort_order or idx + 1,
            )
            self.db.add(question)
        
        self.db.commit()
        self.db.refresh(exam)
        return exam

    # ==================== 数据导入模板 ====================

    def import_questions_to_template(
        self, template_id: int, current_user: User, questions_data: list[dict]
    ) -> dict:
        template = self.get(template_id)
        if not template:
            raise NotFoundException("模板不存在")
        self._ensure_owner_or_admin(template, current_user, "操作")
        
        try:
            # 清空现有题目
            self.db.query(TemplateQuestion).filter(
                TemplateQuestion.template_id == template_id
            ).delete()
            
            # 批量创建新题目
            for idx, q in enumerate(questions_data):
                self._validate_question_data(q)
                question = TemplateQuestion(
                    template_id=template_id,
                    question_no=q.get("question_no"),
                    category=q.get("category"),
                    type=q["type"],
                    content=q["content"],
                    options=q.get("options"),
                    answer=q["answer"],
                    score=q.get("score", 0),
                    sort_order=q.get("sort_order", idx + 1),
                )
                self.db.add(question)
            
            self.db.commit()
            
            return {
                "imported_count": len(questions_data),
                "template_id": template_id,
                "template_name": template.name,
            }
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"导入失败: {str(e)}")

    # ==================== 私有方法 ====================

    def _validate_question_data(self, data: dict) -> None:
        q_type = data.get("type")
        options = data.get("options")
        answer = data.get("answer", "")

        if q_type in ("single_choice", "multiple_choice"):
            if not options or len(options) < 2:
                raise BusinessException(f"{q_type} 题型至少需要 2 个选项")
        elif q_type == "true_false":
            if answer not in ("true", "false"):
                raise BusinessException("判断题答案必须是 'true' 或 'false'")
        elif q_type == "short_answer":
            if not answer or not str(answer).strip():
                raise BusinessException("简答题答案不能为空")
