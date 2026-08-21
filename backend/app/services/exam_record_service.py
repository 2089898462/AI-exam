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
from app.models.exam_monitor_summary import ExamMonitorSummary
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

    def submit_exam(self, record_id: int, monitor_data: dict | None = None) -> ExamRecord:
        """提交考试

        状态流转：in_progress → submitted
        支持幂等提交：已提交/已批改则直接返回当前状态
        
        监考数据保存策略：监考数据保存失败不影响考试提交流程
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
        
        # 先保存考试状态
        try:
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            logger.error(f"提交考试失败: record_id={record_id}")
            raise
            
        # 处理监考数据（独立事务，失败不影响主流程）
        if monitor_data:
            try:
                self._save_monitor_summary(record_id, monitor_data)
            except Exception as e:
                logger.error(f"保存监考数据失败（不影响考试提交）: record_id={record_id}, error={e}")

        duration = record.submitted_at - record.started_at if record.started_at else None
        logger.info(
            f"提交考试: record_id={record_id}, candidate={record.candidate_name}, "
            f"duration={duration}"
        )
        return record

    def _save_monitor_summary(self, record_id: int, monitor_data: dict) -> None:
        """保存监考汇总数据（S8.4.2 增强版）
        
        Args:
            record_id: 考试记录ID
            monitor_data: 监考数据字典
                - leave_count: 离开次数
                - total_hidden_duration: 累计离开时长(毫秒)
                - events: 详细事件列表(可选)
                - environment: 环境采集数据(可选, S8.4.1 新增)
        
        S8.4.2 变更：
        - 新增异常行为分析（analyze_monitor_behavior）
        - 风险计算优化（V3规则）
        - detail_data 扩展 analysis 字段
        """
        # 查询考试记录获取时间信息
        record = self.get_record_by_id(record_id)
        
        # 转换时长为秒
        leave_count = monitor_data.get('leave_count', 0)
        total_duration_ms = monitor_data.get('total_hidden_duration', 0)
        total_duration_seconds = total_duration_ms // 1000  # 毫秒转秒
        
        # 获取详细事件（如果有）
        events = monitor_data.get('events', [])
        
        # S8.4.1: 获取环境采集数据（可选）
        environment = monitor_data.get('environment', None)
        
        # S8.4.2: 执行异常行为分析
        behavior_analysis = self.analyze_monitor_behavior(monitor_data)
        behavior_tags = behavior_analysis.get('behavior_tags', [])
        analysis_data = behavior_analysis.get('analysis', {})
        
        # 计算动态指标
        # 1. 单次最长离开时长（秒）
        max_single_duration = analysis_data.get('max_single_duration', 0)
        
        # 2. 考试总时长（秒）
        exam_duration_seconds = self._calculate_exam_duration(record)
        
        # 3. 离开时间占比（%）
        leave_ratio = self._calculate_leave_ratio(total_duration_seconds, exam_duration_seconds)
        
        # 4. 离开频率（次/小时）
        leave_frequency = self._calculate_leave_frequency(leave_count, exam_duration_seconds)
        
        # S8.4.2: 获取网络相关信息用于风险豁免
        network_related_leaves = analysis_data.get('network_related_leaves', 0)
        rapid_trips = analysis_data.get('rapid_trips', 0)
        max_density = analysis_data.get('max_leave_density', 0.0)
        
        # S8.4.2: 计算风险等级（V3规则，考虑异常标签和网络豁免）
        risk_level = self._calculate_risk_level_v3(
            leave_count=leave_count,
            total_duration_seconds=total_duration_seconds,
            max_single_duration=max_single_duration,
            leave_ratio=leave_ratio,
            leave_frequency=leave_frequency,
            behavior_tags=behavior_tags,
            network_related_leaves=network_related_leaves,
            rapid_trips=rapid_trips,
            max_density=max_density,
        )
        
        # S8.4.2: 序列化 detail_data（结构化 JSON 对象，包含分析结果）
        import json
        detail_obj = {}
        if events:
            detail_obj['events'] = events
        if environment:
            detail_obj['environment'] = environment
        # S8.4.2: 新增 analysis 字段
        detail_obj['analysis'] = {
            'behavior_tags': behavior_tags,
            'risk_reason': behavior_analysis.get('risk_reason', []),
            'max_single_duration': max_single_duration,
            'leave_frequency': leave_frequency,
            'rapid_trips': rapid_trips,
            'max_leave_density': max_density,
            'network_related_leaves': network_related_leaves,
        }
        
        detail_json = json.dumps(detail_obj, ensure_ascii=False) if detail_obj else None
        
        summary = ExamMonitorSummary(
            exam_record_id=record_id,
            leave_count=leave_count,
            total_duration=total_duration_seconds,
            risk_level=risk_level,
            detail_data=detail_json,
        )
        
        self.db.add(summary)
        self.db.commit()
        logger.info(
            f"保存监考汇总: record_id={record_id}, leave_count={leave_count}, "
            f"total_duration={total_duration_seconds}s, risk_level={risk_level}, "
            f"max_single={max_single_duration}s, leave_ratio={leave_ratio:.1f}%, "
            f"behavior_tags={behavior_tags}"
        )

    @staticmethod
    def _calculate_max_single_duration(events: list) -> int:
        """计算单次最长离开时长（秒）

        S8.4.1: 只计算 exam_leave 类型事件的 duration
        （events 可能包含 orientation_change、network_offline 等非离开事件）
        S8.4.6: leave_recovered 事件（S8.4.4 异常中断补偿）也携带真实离开时长，
        需一并纳入计算，否则该场景下单次最长离开会被低估
        """
        if not events:
            return 0

        max_duration_ms = 0
        for event in events:
            # 计算 exam_leave 与 leave_recovered 事件的持续时间
            if event.get('type') in ('exam_leave', 'leave_recovered'):
                duration = event.get('duration', 0)
                if duration > max_duration_ms:
                    max_duration_ms = duration

        return max_duration_ms // 1000  # 毫秒转秒

    @staticmethod
    def _calculate_exam_duration(record) -> int:
        """计算考试总时长（秒）
        
        优先使用 submitted_at - started_at
        如果 submitted_at 为空，使用当前时间
        如果 started_at 为空，返回默认值 0
        """
        if not record or not record.started_at:
            return 0
        
        try:
            from datetime import datetime
            end_time = record.submitted_at or datetime.now()
            duration = (end_time - record.started_at).total_seconds()
            return max(int(duration), 0)  # 确保非负
        except Exception:
            return 0

    @staticmethod
    def _calculate_leave_ratio(total_duration_seconds: int, exam_duration_seconds: int) -> float:
        """计算离开时间占比（%）
        
        leave_ratio = total_duration / exam_duration * 100
        如果考试时长为0，返回0
        """
        if exam_duration_seconds <= 0:
            return 0.0
        return round(total_duration_seconds / exam_duration_seconds * 100, 2)

    @staticmethod
    def _calculate_leave_frequency(leave_count: int, exam_duration_seconds: int) -> float:
        """计算离开频率（次/小时）
        
        leave_frequency = leave_count / (exam_duration / 3600)
        如果考试时长为0，返回0
        """
        if exam_duration_seconds <= 0:
            return 0.0
        exam_hours = exam_duration_seconds / 3600.0
        return round(leave_count / exam_hours, 2) if exam_hours > 0 else 0.0

    @staticmethod
    def _calculate_risk_level_v2(
        leave_count: int,
        total_duration_seconds: int,
        max_single_duration: int,
        leave_ratio: float,
        leave_frequency: float,
    ) -> str:
        """计算风险等级 V2（多维度评估）
        
        优化规则：
        1. 无离开：normal
        2. 短时间少量离开：max_single_duration < 30秒 且 leave_count <= 3 → low
        3. 高风险：max_single_duration >= 300秒 或 leave_ratio >= 20% 或 leave_count > 8 → high
        4. 其他：medium
        
        设计理念：
        - 关注单次异常：区分"1次5分钟"vs"5次1分钟"
        - 关注影响程度：离开时间占比更能反映影响
        - 关注行为模式：高频离开可能是作弊
        - 容忍合理打断：短时间少量离开视为正常打断
        
        注意：风险等级仅为辅助指标，不等同于作弊判定
        """
        # 规则1：无离开 → 正常
        if leave_count == 0:
            return "normal"
        
        # 规则2：高风险（满足任一条件）
        # - 单次最长离开 >= 5分钟（300秒）
        # - 离开时间占比 >= 20%
        # - 离开次数 > 8次
        if max_single_duration >= 300 or leave_ratio >= 20.0 or leave_count > 8:
            return "high"
        
        # 规则3：低风险（短时间少量离开）
        # - 单次最长离开 < 30秒
        # - 离开次数 <= 3次
        if max_single_duration < 30 and leave_count <= 3:
            return "low"
        
        # 规则4：中风险（其余情况）
        return "medium"

    @staticmethod
    def _calculate_risk_level_v3(
        leave_count: int,
        total_duration_seconds: int,
        max_single_duration: int,
        leave_ratio: float,
        leave_frequency: float,
        behavior_tags: list = None,
        network_related_leaves: int = 0,
        rapid_trips: int = 0,
        max_density: float = 0.0,
    ) -> str:
        """S8.4.2: 计算风险等级 V3（增强规则）
        
        基于 V2 规则，新增：
        - 网络异常豁免：所有离开都是网络相关时，降级为 normal
        - 快速往返高频次：rapid_trips >= 3 → high
        - 集中式异常：max_density > 0.6 → 至少 medium
        - 行为标签辅助判定
        
        Args:
            leave_count: 离开次数
            total_duration_seconds: 累计离开时长（秒）
            max_single_duration: 单次最长离开时长（秒）
            leave_ratio: 离开时间占比（%）
            leave_frequency: 离开频率（次/小时）
            behavior_tags: 异常行为标签列表
            network_related_leaves: 网络相关离开次数
            rapid_trips: 快速往返次数
            max_density: 最大切屏密度（次/分钟）
        
        Returns:
            str: 风险等级 normal/low/medium/high
        """
        behavior_tags = behavior_tags or []
        
        # 规则1：无离开 → 正常
        if leave_count == 0:
            return "normal"
        
        # S8.4.2 新增规则：网络异常豁免
        # 如果所有离开都是网络相关（网络异常导致），直接判定为正常
        if network_related_leaves >= leave_count and leave_count > 0:
            return "normal"
        
        # S8.4.2 新增规则：快速往返高频次 → 高风险
        if rapid_trips >= 3:
            return "high"
        
        # S8.4.2 新增规则：单次超长离开 → 高风险
        if max_single_duration >= 300:
            return "high"
        
        # S8.4.2 新增规则：离开时间占比过高 → 高风险
        if leave_ratio >= 20.0:
            return "high"
        
        # S8.4.2 新增规则：离开次数过多 → 高风险
        if leave_count > 8:
            return "high"
        
        # S8.4.2 新增规则：集中式异常（密度 > 1次/分钟）→ 至少 medium
        if max_density > 1.0:
            return "medium"
        
        # S8.4.2 新增规则：高频标签 + 多次离开 → medium
        if 'frequent_leave' in behavior_tags and leave_count >= 3:
            return "medium"
        
        # S8.4.2 新增规则：快速往返（但次数少）→ 低风险
        if rapid_trips >= 1 and rapid_trips < 3:
            return "low"
        
        # S8.4.2 新增规则：长时间离开（但未达5分钟）→ 至少 medium
        if max_single_duration >= 60 and 'long_leave' in behavior_tags:
            return "medium"
        
        # 规则3：低风险（短时间少量离开）
        if max_single_duration < 30 and leave_count <= 3:
            return "low"
        
        # 规则4：中风险（其余情况）
        return "medium"

    # ============ S8.4.2: 异常行为分析 ============

    @staticmethod
    def _count_rapid_trips(events: list, threshold: int = 5) -> int:
        """计算快速往返次数（离开后 threshold 秒内返回）
        
        Args:
            events: 事件列表
            threshold: 阈值（秒），默认5秒
        
        Returns:
            int: 快速往返次数
        """
        if not events:
            return 0
        
        rapid_count = 0
        leave_events = [e for e in events if e.get('type') == 'exam_leave']
        return_events = [e for e in events if e.get('type') == 'exam_return']
        
        for leave in leave_events:
            leave_time = leave.get('timestamp', 0)
            # 找最近的 return 事件
            for ret in return_events:
                ret_time = ret.get('timestamp', 0)
                if ret_time > leave_time:
                    duration_ms = ret.get('duration', 0)
                    if 0 < duration_ms <= threshold * 1000:
                        rapid_count += 1
                    break
        
        return rapid_count

    @staticmethod
    def _count_network_related_leaves(events: list) -> int:
        """统计网络异常相关的离开次数
        
        离开发生在 network_offline 事件后30秒内，视为网络相关
        """
        if not events:
            return 0
        
        offline_times = [
            e.get('timestamp', 0)
            for e in events
            if e.get('type') == 'network_offline'
        ]
        
        if not offline_times:
            return 0
        
        network_related_count = 0
        for event in events:
            if event.get('type') == 'exam_leave':
                leave_time = event.get('timestamp', 0)
                # 检查是否在某个 offline 事件后30秒内
                is_related = any(
                    0 < (leave_time - offline_time) <= 30000
                    for offline_time in offline_times
                )
                if is_related:
                    network_related_count += 1
        
        return network_related_count

    @staticmethod
    def _calc_max_leave_density(events: list, window_minutes: int = 5) -> float:
        """计算最大切屏密度（次/分钟）
        
        在指定时间窗口内计算最高切屏频率
        """
        if not events:
            return 0.0
        
        leave_events = [e for e in events if e.get('type') == 'exam_leave']
        if len(leave_events) < 2:
            return 0.0
        
        timestamps = sorted([e['timestamp'] for e in leave_events])
        window_ms = window_minutes * 60 * 1000
        max_density = 0.0
        
        for i in range(len(timestamps)):
            window_end = timestamps[i] + window_ms
            count = sum(1 for t in timestamps[i:] if t <= window_end)
            density = count / window_minutes
            max_density = max(max_density, density)
        
        return round(max_density, 2)

    @staticmethod
    def analyze_monitor_behavior(monitor_data: dict) -> dict:
        """S8.4.2: 分析监考行为，生成异常标签和风险原因
        
        Args:
            monitor_data: 前端上报的监考数据
        
        Returns:
            dict: {behavior_tags: [], risk_reason: [], analysis: {...}}
        """
        events = monitor_data.get('events', [])
        leave_count = monitor_data.get('leave_count', 0)
        total_duration_ms = monitor_data.get('total_hidden_duration', 0)
        total_duration_s = total_duration_ms // 1000
        
        behavior_tags = []
        risk_reasons = []
        
        # 1. 检查快速往返
        rapid_trips = ExamRecordService._count_rapid_trips(events)
        if rapid_trips >= 1:
            behavior_tags.append('rapid_leave_return')
            risk_reasons.append(f'检测到{rapid_trips}次快速离开返回（5秒内）')
        
        # 2. 检查长时间离开
        max_single_duration = ExamRecordService._calculate_max_single_duration(events)
        if max_single_duration >= 60:
            behavior_tags.append('long_leave')
            risk_reasons.append(f'存在单次长达{max_single_duration}秒的离开')
        
        # 3. 检查高频离开（基于标签 + 密度计算）
        leave_events_with_tags = [
            e for e in events
            if e.get('type') == 'exam_leave' and 'frequent_leave' in (e.get('tags') or [])
        ]
        density = ExamRecordService._calc_max_leave_density(events)
        if leave_events_with_tags or density > 0.6:  # > 0.6次/分钟 = 5分钟内>3次
            behavior_tags.append('frequent_leave')
            if density > 0:
                risk_reasons.append(f'离开行为集中，最大密度{density}次/分钟')
        
        # 4. 检查网络相关
        network_related = ExamRecordService._count_network_related_leaves(events)
        if network_related > 0:
            behavior_tags.append('network_related')
            risk_reasons.append(f'其中{network_related}次离开与网络异常相关')
        
        # 5. 检查刷新尝试
        refresh_attempts = len([e for e in events if e.get('type') == 'refresh_attempt'])
        if refresh_attempts > 0:
            behavior_tags.append('refresh_attempt')
            risk_reasons.append(f'检测到{refresh_attempts}次页面刷新尝试')
        
        # 汇总
        result = {
            'behavior_tags': behavior_tags,
            'risk_reason': risk_reasons,
            'analysis': {
                'rapid_trips': rapid_trips,
                'max_single_duration': max_single_duration,
                'max_leave_density': density,
                'network_related_leaves': network_related,
                'refresh_attempts': refresh_attempts,
                'total_leave_count': leave_count,
                'total_duration': total_duration_s,
            }
        }
        
        return result

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
