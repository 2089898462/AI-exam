"""
考试记录 & 答题记录服务（兼容层）
S3.1.2: 已拆分 ExamRecordService + AnswerRecordService
本模块保留 RecordService 用于向后兼容
"""
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.answer_record import AnswerRecord
from app.models.exam_record import ExamRecord
from app.services.answer_record_service import AnswerRecordService
from app.services.exam_record_service import ExamRecordService


class RecordService:
    """考试记录业务逻辑（兼容封装）"""

    def __init__(self, db: Session):
        self.db = db
        self._exam_record_svc = ExamRecordService(db)
        self._answer_record_svc = AnswerRecordService(db)

    def start_exam(
        self,
        exam_id: int,
        candidate_name: str,
        candidate_phone: str | None = None,
        candidate_email: str | None = None,
    ) -> ExamRecord:
        """候选人进入考试（创建记录 + 直接开始）"""
        record = self._exam_record_svc.create_exam_record(
            exam_id=exam_id,
            candidate_name=candidate_name,
            candidate_phone=candidate_phone,
            candidate_email=candidate_email,
        )
        return self._exam_record_svc.start_exam(record.id)

    def submit_exam(self, record_id: int) -> ExamRecord:
        """提交考试"""
        return self._exam_record_svc.submit_exam(record_id)

    def save_answer(
        self,
        record_id: int,
        question_id: int,
        answer_content: str | None,
    ) -> AnswerRecord:
        """保存单题答案"""
        return self._answer_record_svc.save_answer(
            record_id=record_id,
            question_id=question_id,
            answer_content=answer_content,
        )

    def get_by_exam(self, exam_id: int) -> list[ExamRecord]:
        """获取某考试的所有记录"""
        return self._exam_record_svc.list_exam_records(exam_id=exam_id)

    def get_detail_with_answers(self, record_id: int) -> ExamRecord:
        """获取考试记录详情（含答题记录）"""
        return self._exam_record_svc.get_detail_with_answers(record_id)
