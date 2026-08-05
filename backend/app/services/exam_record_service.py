"""
考试记录Service
管理候选人考试记录的创建、状态流转、查询
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.exam_record import ExamRecord
from app.services.base import BaseService


class ExamRecordService(BaseService[ExamRecord]):
    """考试记录业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, ExamRecord)

    def create_exam_record(
        self,
        exam_id: int,
        candidate_name: str,
        candidate_phone: str | None = None,
        candidate_email: str | None = None,
    ) -> ExamRecord:
        """创建候选人考试记录

        校验：
        - 考试必须存在
        - 候选人姓名不为空

        初始状态：not_started（未开始）
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        if not candidate_name or not candidate_name.strip():
            raise BusinessException("候选人姓名不能为空")

        record = ExamRecord(
            exam_id=exam_id,
            candidate_name=candidate_name.strip(),
            candidate_phone=candidate_phone,
            candidate_email=candidate_email,
            status="not_started",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_record_by_id(self, record_id: int) -> ExamRecord:
        """查询考试记录"""
        record = self.get(record_id)
        if not record:
            raise NotFoundException("考试记录不存在")
        return record

    def start_exam(self, record_id: int) -> ExamRecord:
        """开始考试

        状态流转：not_started → in_progress
        记录 started_at 时间戳
        """
        record = self.get_record_by_id(record_id)
        if record.status != "not_started":
            raise BusinessException(f"考试记录状态为 {record.status}，无法开始")

        record.status = "in_progress"
        record.started_at = datetime.now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def submit_exam(self, record_id: int) -> ExamRecord:
        """提交考试

        状态流转：in_progress → submitted
        记录 submitted_at 时间戳
        """
        record = self.get_record_by_id(record_id)
        if record.status != "in_progress":
            raise BusinessException(f"考试记录状态为 {record.status}，无法提交")

        record.status = "submitted"
        record.submitted_at = datetime.now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_exam_records(
        self,
        exam_id: int,
        status: str | None = None,
    ) -> list[ExamRecord]:
        """根据考试ID查询候选人考试记录列表"""
        query = self.db.query(ExamRecord).filter(ExamRecord.exam_id == exam_id)
        if status:
            query = query.filter(ExamRecord.status == status)
        return query.order_by(ExamRecord.created_at.desc()).all()

    def get_detail_with_answers(self, record_id: int) -> ExamRecord:
        """获取考试记录详情（含答题记录和考试信息）"""
        record = self.get_record_by_id(record_id)
        _ = record.answer_records
        _ = record.exam
        return record
