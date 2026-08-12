"""
考试记录Service
管理候选人考试记录的创建、状态流转、查询

事务保护：
- 所有写操作使用 try/except 包裹
- 异常时自动 rollback，防止脏数据
- 记录操作日志便于追踪
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.exam_participant import ExamParticipant
from app.models.exam_record import ExamRecord
from app.services.base import BaseService

logger = get_logger(__name__)


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
        exam_code: str | None = None,
    ) -> ExamRecord:
        """创建候选人考试记录（含安全校验）"""
        # 1. 考试存在性与状态校验
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")
        if exam.status != "published":
            raise BusinessException(f"考试状态为 {exam.status}，无法参加")

        # 2. 考试凭证校验 (如果考试设置了凭证)
        if exam.exam_code:
            if not exam_code or exam_code.strip() != exam.exam_code:
                raise BusinessException("考试访问凭证错误")
        elif exam_code:
            # 如果考试没有设置凭证，但候选人提交了凭证，给出提示或忽略
            # 为安全起见，如果考试有 exam_code 字段但未设置，允许无凭证进入
            pass

        # 3. 候选人身份与参与资格校验
        # 检查考试是否有指定参与者
        participant_count = self.db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam_id
        ).count()
        
        if participant_count > 0:
            # 考试有指定参与者，需要校验身份
            if not candidate_phone:
                raise BusinessException("该考试需要预先登记的候选人信息，请填写手机号")
            
            participant = self.db.query(ExamParticipant).filter(
                ExamParticipant.exam_id == exam_id,
                ExamParticipant.candidate_phone == candidate_phone
            ).first()
            if not participant:
                raise BusinessException("您未被分配到此考试，无法参加")
        else:
            # 考试没有指定参与者，任何人可通过考试码参加
            participant = None

        if candidate_phone:
            # 检查是否已有未完成的考试记录（防重复创建）
            existing_record = self.db.query(ExamRecord).filter(
                ExamRecord.exam_id == exam_id,
                ExamRecord.candidate_phone == candidate_phone,
                ExamRecord.status.in_(["not_started", "in_progress"])
            ).first()
            if existing_record:
                logger.info(f"候选人 {candidate_phone} 已有未完成的考试记录 {existing_record.id}")
                return existing_record
                
            # 检查是否已提交或已批改（禁止再次提交）
            completed_record = self.db.query(ExamRecord).filter(
                ExamRecord.exam_id == exam_id,
                ExamRecord.candidate_phone == candidate_phone,
                ExamRecord.status.in_(["submitted", "graded"])
            ).first()
            if completed_record:
                raise BusinessException("您已完成此考试，无法再次参加")

        if not candidate_name or not candidate_name.strip():
            raise BusinessException("候选人姓名不能为空")

        record = ExamRecord(
            exam_id=exam_id,
            exam_code=exam.exam_code,
            candidate_name=candidate_name.strip(),
            candidate_phone=candidate_phone,
            candidate_email=candidate_email,
            status="not_started",
        )
        
        # 如果找到了对应的参与者，关联 ID
        if candidate_phone and participant:
            record.participant_id = participant.id
            
        self.db.add(record)
        try:
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            logger.error(f"创建考试记录失败: exam_id={exam_id}")
            raise
        logger.info(
            f"创建考试记录: record_id={record.id}, exam_id={exam_id}, "
            f"candidate={candidate_name.strip()}"
        )
        return record

    def get_record_by_id(self, record_id: int) -> ExamRecord:
        """查询考试记录"""
        record = self.get(record_id)
        if not record:
            raise NotFoundException("考试记录不存在")
        return record

    def start_exam(self, record_id: int) -> ExamRecord:
        """开始考试"""
        record = self.get_record_by_id(record_id)
        if record.status != "not_started":
            raise BusinessException(f"考试记录状态为 {record.status}，无法开始")

        record.status = "in_progress"
        record.started_at = datetime.now()
        try:
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            logger.error(f"开始考试失败: record_id={record_id}")
            raise
        logger.info(f"开始考试: record_id={record_id}, candidate={record.candidate_name}")
        return record

    def submit_exam(self, record_id: int) -> ExamRecord:
        """提交考试

        状态流转：in_progress → submitted
        支持幂等提交：已提交/已批改则直接返回当前状态
        """
        record = self.get_record_by_id(record_id)

        # 幂等：已提交直接返回
        if record.status == "submitted":
            return record

        if record.status == "not_started":
            raise BusinessException("考试尚未开始，无法提交")

        if record.status == "graded":
            return record

        # in_progress 状态正常提交
        record.status = "submitted"
        record.submitted_at = datetime.now()
        try:
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            logger.error(f"提交考试失败: record_id={record_id}")
            raise
        duration = record.submitted_at - record.started_at if record.started_at else None
        logger.info(
            f"提交考试: record_id={record_id}, candidate={record.candidate_name}, "
            f"duration={duration}"
        )
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
