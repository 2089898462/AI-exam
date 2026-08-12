"""
考试参与人员 Service
管理考试与参与人员之间的关系
"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.exam_participant import ExamParticipant
from app.models.exam_record import ExamRecord
from app.models.user import User
from app.services.base import BaseService


class ExamParticipantService(BaseService[ExamParticipant]):
    """考试参与人员业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, ExamParticipant)

    def add_participant(
        self,
        exam_id: int,
        candidate_name: str,
        candidate_phone: str | None = None,
        candidate_email: str | None = None,
        user_id: int | None = None,
    ) -> ExamParticipant:
        """添加考试参与人员"""
        # 检查考试是否存在
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException(f"考试 {exam_id} 不存在")

        # 校验必填字段
        if not candidate_name or not candidate_name.strip():
            raise BusinessException("候选人姓名不能为空")

        # 检查是否重复添加
        query = self.db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam_id)
        
        # 优先根据手机号判断重复
        if candidate_phone:
            existing = query.filter(ExamParticipant.candidate_phone == candidate_phone).first()
            if existing:
                raise BusinessException(f"手机号 {candidate_phone} 已添加到该考试")
        
        # 如果没有手机号，根据姓名+邮箱判断
        if not candidate_phone and candidate_email:
            existing = query.filter(
                ExamParticipant.candidate_name == candidate_name.strip(),
                ExamParticipant.candidate_email == candidate_email
            ).first()
            if existing:
                raise BusinessException(f"候选人 {candidate_name} 已添加到该考试")

        # 创建参与记录
        participant = ExamParticipant(
            exam_id=exam_id,
            user_id=user_id,
            candidate_name=candidate_name.strip(),
            candidate_phone=candidate_phone,
            candidate_email=candidate_email,
            status="assigned",
        )
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def add_participants_batch(
        self,
        exam_id: int,
        participants: list[dict],
    ) -> tuple[int, list[str]]:
        """批量添加考试人员
        
        返回：(成功数量, 错误信息列表)
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException(f"考试 {exam_id} 不存在")

        success_count = 0
        errors = []
        seen_phones = set()

        for p in participants:
            candidate_name = p.get("candidate_name", "").strip()
            candidate_phone = p.get("candidate_phone")
            candidate_email = p.get("candidate_email")
            user_id = p.get("user_id")

            if not candidate_name:
                errors.append(f"姓名不能为空")
                continue

            # 检查手机号重复（在本次批量中）
            if candidate_phone and candidate_phone in seen_phones:
                errors.append(f"手机号 {candidate_phone} 在批量中重复")
                continue

            # 检查数据库中是否已存在
            query = self.db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam_id)
            if candidate_phone:
                existing = query.filter(ExamParticipant.candidate_phone == candidate_phone).first()
                if existing:
                    errors.append(f"手机号 {candidate_phone} 已存在")
                    continue
                seen_phones.add(candidate_phone)
            elif candidate_email:
                existing = query.filter(
                    ExamParticipant.candidate_name == candidate_name,
                    ExamParticipant.candidate_email == candidate_email
                ).first()
                if existing:
                    errors.append(f"{candidate_name} ({candidate_email}) 已存在")
                    continue

            # 创建参与记录
            participant = ExamParticipant(
                exam_id=exam_id,
                user_id=user_id,
                candidate_name=candidate_name,
                candidate_phone=candidate_phone,
                candidate_email=candidate_email,
                status="assigned",
            )
            self.db.add(participant)
            success_count += 1

        self.db.commit()
        return success_count, errors

    def list_participants(
        self,
        exam_id: int,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """查询考试参与人员列表（含状态和是否完成）"""
        query = self.db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam_id)

        if status:
            query = query.filter(ExamParticipant.status == status)

        if keyword:
            filters = [
                ExamParticipant.candidate_name.contains(keyword),
                ExamParticipant.candidate_phone.contains(keyword),
                ExamParticipant.candidate_email.contains(keyword),
            ]
            query = query.filter(or_(*filters))

        total = query.count()
        participants = query.order_by(ExamParticipant.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        # 查询每个参与人员的考试记录
        result = []
        for p in participants:
            record = self.db.query(ExamRecord).filter(
                ExamRecord.exam_id == exam_id,
                ExamRecord.candidate_name == p.candidate_name,
            ).first()

            # 如果有手机号，尝试更精确匹配
            if p.candidate_phone and not record:
                record = self.db.query(ExamRecord).filter(
                    ExamRecord.exam_id == exam_id,
                    ExamRecord.candidate_phone == p.candidate_phone,
                ).first()

            # 确定完成状态
            completed = False
            exam_record_status = None
            if record:
                completed = record.status in ("submitted", "graded")
                exam_record_status = record.status

            result.append({
                "id": p.id,
                "exam_id": p.exam_id,
                "user_id": p.user_id,
                "candidate_name": p.candidate_name,
                "candidate_phone": p.candidate_phone,
                "candidate_email": p.candidate_email,
                "status": p.status,
                "completed": completed,
                "exam_record_status": exam_record_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        return result, total

    def get_participant(self, participant_id: int) -> ExamParticipant:
        """获取单个参与人员详情"""
        participant = self.get(participant_id)
        if not participant:
            raise NotFoundException("参与人员不存在")
        return participant

    def remove_participant(self, participant_id: int) -> bool:
        """删除参与人员（只能删除未参加考试的人员）"""
        participant = self.get(participant_id)
        if not participant:
            raise NotFoundException("参与人员不存在")

        # 检查是否已有考试记录
        record = self.db.query(ExamRecord).filter(
            ExamRecord.exam_id == participant.exam_id,
            ExamRecord.candidate_name == participant.candidate_name,
        ).first()

        # 如果有手机号，尝试更精确匹配
        if participant.candidate_phone and not record:
            record = self.db.query(ExamRecord).filter(
                ExamRecord.exam_id == participant.exam_id,
                ExamRecord.candidate_phone == participant.candidate_phone,
            ).first()

        if record:
            raise BusinessException(
                f"参与人员 {participant.candidate_name} 已有考试记录，无法删除。"
                f"请使用关闭考试功能处理。"
            )

        return self.delete(participant_id)

    def update_participant_status(
        self,
        participant_id: int,
        status: str,
    ) -> ExamParticipant:
        """更新参与人员状态"""
        participant = self.get(participant_id)
        if not participant:
            raise NotFoundException("参与人员不存在")

        valid_statuses = ("assigned", "not_started", "in_progress", "submitted", "completed")
        if status not in valid_statuses:
            raise BusinessException(f"无效的状态值: {status}")

        participant.status = status
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def sync_status_from_exam_record(self, exam_id: int) -> int:
        """同步参与人员状态（从 ExamRecord 获取状态）
        
        返回同步更新的数量
        """
        participants = self.db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam_id
        ).all()

        updated_count = 0
        for p in participants:
            record = self.db.query(ExamRecord).filter(
                ExamRecord.exam_id == exam_id,
                ExamRecord.candidate_name == p.candidate_name,
            ).first()

            # 如果有手机号，尝试更精确匹配
            if p.candidate_phone and not record:
                record = self.db.query(ExamRecord).filter(
                    ExamRecord.exam_id == exam_id,
                    ExamRecord.candidate_phone == p.candidate_phone,
                ).first()

            if record:
                new_status = self._map_record_status_to_participant(record.status)
                if new_status != p.status:
                    p.status = new_status
                    updated_count += 1

        if updated_count > 0:
            self.db.commit()

        return updated_count

    @staticmethod
    def _map_record_status_to_participant(record_status: str) -> str:
        """将考试记录状态映射为参与人员状态"""
        mapping = {
            "not_started": "not_started",
            "in_progress": "in_progress",
            "submitted": "submitted",
            "graded": "completed",
        }
        return mapping.get(record_status, "assigned")

    def get_participant_count(self, exam_id: int) -> dict:
        """获取考试参与人员统计"""
        base_query = self.db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam_id)

        total = base_query.count()
        assigned = base_query.filter(ExamParticipant.status == "assigned").count()
        not_started = base_query.filter(ExamParticipant.status == "not_started").count()
        in_progress = base_query.filter(ExamParticipant.status == "in_progress").count()
        submitted = base_query.filter(ExamParticipant.status.in_(["submitted", "completed"])).count()

        return {
            "total": total,
            "assigned": assigned,
            "not_started": not_started,
            "in_progress": in_progress,
            "completed": submitted,
        }
