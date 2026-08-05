"""
考试导入服务
负责解析 JSON 文件并导入考试数据
"""
import json

from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.exam import Exam
from app.models.question import Question
from app.models.user import User
from app.schemas.exam_import import ExamImportSchema


TYPE_MAP = {
    "single_choice": "single_choice",
    "multiple_choice": "multiple_choice",
    "essay": "short_answer",
}


class ExamImportService:
    """考试 JSON 导入服务"""

    def __init__(self, db: Session):
        self.db = db

    def import_exam(self, exam_id: int, current_user: User, json_data: dict) -> dict:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        if current_user.role != "admin" and exam.created_by != current_user.id:
            raise BusinessException("无权操作此考试")
        if exam.status != "draft":
            raise BusinessException("只有草稿状态的考试才能导入题目")

        try:
            validated = ExamImportSchema(**json_data)
        except Exception as e:
            errors = self._extract_validation_errors(e)
            raise ValidationException(data={"errors": errors})

        try:
            exam.title = validated.title
            if validated.position is not None:
                exam.position = validated.position
            if validated.description is not None:
                exam.description = validated.description
            if validated.duration_minutes is not None:
                exam.duration_minutes = validated.duration_minutes
            exam.pass_score = validated.pass_score
            if validated.exam_code is not None:
                exam.exam_code = validated.exam_code

            existing_count = (
                self.db.query(Question)
                .filter(Question.exam_id == exam_id)
                .count()
            )

            questions_to_add = []
            for idx, q in enumerate(validated.questions):
                db_type = TYPE_MAP.get(q.type)
                sort_order = q.sort_order if q.sort_order > 0 else existing_count + idx + 1

                question_data = {
                    "exam_id": exam_id,
                    "type": db_type,
                    "content": q.content,
                    "question_no": q.question_no,
                    "category": q.category,
                    "answer": q.answer,
                    "score": q.score,
                    "sort_order": sort_order,
                }

                if q.options and db_type in ("single_choice", "multiple_choice"):
                    question_data["options"] = [
                        {"label": opt.label, "text": opt.text} for opt in q.options
                    ]

                questions_to_add.append(question_data)

            self.db.bulk_insert_mappings(Question, questions_to_add)
            self.db.commit()

            return {
                "imported_count": len(questions_to_add),
                "exam_id": exam_id,
                "exam_title": exam.title,
            }

        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"导入失败: {str(e)}")

    def _extract_validation_errors(self, exc: Exception) -> list[str]:
        errors = []
        if hasattr(exc, "errors"):
            err_list = exc.errors() if callable(exc.errors) else exc.errors
            for err in err_list:
                loc = err.get("loc", ())
                msg = err.get("msg", str(err))
                if loc:
                    field_path = ".".join(str(l) for l in loc)
                    errors.append(f"{field_path}: {msg}")
                else:
                    errors.append(msg)
        else:
            errors.append(str(exc))
        return errors