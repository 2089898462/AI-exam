"""
考试统计 Service
提供考试数据聚合计算能力

职责：
- 考试整体统计（参与人数、平均分、通过率等）
- 候选人历史考试查询

数据来源：
- Exam
- ExamParticipant
- ExamRecord
- GradingRecord

统计逻辑特点：
- 实时计算，不存储冗余数据
- 空数据安全处理
- 支持多种筛选条件
"""
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.models.answer_record import AnswerRecord
from app.models.exam import Exam
from app.models.exam_participant import ExamParticipant
from app.models.exam_record import ExamRecord
from app.models.grading_record import GradingRecord
from app.models.question import Question
from app.models.user import User

logger = get_logger(__name__)


class ExamStatisticsService:
    """考试统计业务逻辑"""

    def __init__(self, db: Session):
        self.db = db

    def get_exam_statistics(
        self,
        exam_id: int,
        current_user: User,
    ) -> dict:
        """获取考试统计数据

        Args:
            exam_id: 考试 ID
            current_user: 当前用户（权限校验）

        Returns:
            dict: 考试统计数据

        Raises:
            NotFoundException: 考试不存在
            ForbiddenException: 无权限访问
        """
        # 1. 获取考试信息
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        # 2. 权限校验
        self._check_view_permission(exam, current_user)

        # 3. 获取基础数据
        result = {
            "exam_id": exam.id,
            "exam_title": exam.title,
            "exam_status": exam.status,
            "pass_score": float(exam.pass_score),
            "total_participants": 0,
            "completed_count": 0,
            "unfinished_count": 0,
            "average_score": None,
            "max_score": None,
            "min_score": None,
            "pass_count": 0,
            "pass_rate": None,
        }

        # 4. 统计参与人数
        total_participants = self.db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam_id
        ).count()
        result["total_participants"] = total_participants

        # 5. 获取已提交的考试记录
        submitted_records = self.db.query(ExamRecord).filter(
            ExamRecord.exam_id == exam_id,
            ExamRecord.status.in_(["submitted", "graded"]),
        ).all()

        completed_count = len(submitted_records)
        result["completed_count"] = completed_count

        # 6. 计算未完成人数（参与人数 - 已完成人数）
        result["unfinished_count"] = max(0, total_participants - completed_count)

        # 7. 计算成绩统计
        if submitted_records:
            scores = []
            pass_score = float(exam.pass_score)
            pass_count = 0

            for record in submitted_records:
                # 获取评分记录
                grading = self.db.query(GradingRecord).filter(
                    GradingRecord.exam_record_id == record.id
                ).first()

                if grading and grading.total_score is not None:
                    score = float(grading.total_score)
                    scores.append(score)
                    if score >= pass_score:
                        pass_count += 1
                elif record.score is not None:
                    score = float(record.score)
                    scores.append(score)
                    if score >= pass_score:
                        pass_count += 1

            if scores:
                result["average_score"] = round(sum(scores) / len(scores), 2)
                result["max_score"] = round(max(scores), 2)
                result["min_score"] = round(min(scores), 2)

            result["pass_count"] = pass_count
            result["pass_rate"] = round(pass_count / completed_count * 100, 1) if completed_count > 0 else 0.0

        return result

    def get_candidate_exam_history(
        self,
        candidate_id: int,
        current_user: User,
    ) -> dict:
        """获取候选人历史考试记录

        Args:
            candidate_id: 候选人 ID（User ID）
            current_user: 当前用户（权限校验）

        Returns:
            dict: 候选人历史考试记录

        Raises:
            NotFoundException: 候选人不存在
            ForbiddenException: 无权限访问
        """
        # 1. 获取候选人信息
        candidate = self.db.query(User).filter(User.id == candidate_id).first()
        if not candidate:
            raise NotFoundException("候选人不存在")

        # 2. 权限校验
        self._check_candidate_history_permission(candidate_id, current_user)

        # 3. 查询候选人参与的所有考试记录
        records = self.db.query(ExamRecord).filter(
            ExamRecord.candidate_phone == candidate.phone,
        ).order_by(ExamRecord.created_at.desc()).all()

        # 如果候选人没有 phone，尝试用其他方式查询
        if not records and candidate.email:
            records = self.db.query(ExamRecord).filter(
                or_(
                    ExamRecord.candidate_phone == candidate.phone,
                    ExamRecord.candidate_email == candidate.email,
                )
            ).order_by(ExamRecord.created_at.desc()).all()

        # 4. 构建历史记录
        history_items = []
        for record in records:
            exam = self.db.query(Exam).filter(Exam.id == record.exam_id).first()
            if not exam:
                continue

            # 获取评分信息
            grading = self.db.query(GradingRecord).filter(
                GradingRecord.exam_record_id == record.id
            ).first()

            item = {
                "exam_record_id": record.id,
                "exam_id": exam.id,
                "exam_title": exam.title,
                "exam_position": exam.position,
                "exam_status": exam.status,
                "record_status": record.status,
                "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "score": float(grading.total_score) if grading and grading.total_score else (
                    float(record.score) if record.score else None
                ),
                "passed": grading.passed if grading else None,
                "pass_score": float(exam.pass_score),
            }
            history_items.append(item)

        return {
            "candidate_id": candidate_id,
            "candidate_name": candidate.display_name or candidate.username,
            "total_exams": len(history_items),
            "completed_exams": len([r for r in history_items if r["record_status"] in ("submitted", "graded")]),
            "passed_exams": len([r for r in history_items if r["passed"] is True]),
            "failed_exams": len([r for r in history_items if r["passed"] is False]),
            "history": history_items,
        }

    def get_candidate_history_by_phone(
        self,
        phone: str,
        current_user: User,
    ) -> dict:
        """通过手机号获取候选人历史考试记录

        Args:
            phone: 候选人手机号
            current_user: 当前用户（权限校验）

        Returns:
            dict: 候选人历史考试记录
        """
        # 1. 权限校验
        self._check_hr_or_admin(current_user)

        # 2. 查询候选人是否存在于用户表
        candidate = self.db.query(User).filter(User.phone == phone).first()

        # 3. 查询考试记录
        records = self.db.query(ExamRecord).filter(
            ExamRecord.candidate_phone == phone,
        ).order_by(ExamRecord.created_at.desc()).all()

        # 4. 构建历史记录
        history_items = []
        for record in records:
            exam = self.db.query(Exam).filter(Exam.id == record.exam_id).first()
            if not exam:
                continue

            grading = self.db.query(GradingRecord).filter(
                GradingRecord.exam_record_id == record.id
            ).first()

            item = {
                "exam_record_id": record.id,
                "exam_id": exam.id,
                "exam_title": exam.title,
                "exam_position": exam.position,
                "exam_status": exam.status,
                "record_status": record.status,
                "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
                "score": float(grading.total_score) if grading and grading.total_score else None,
                "passed": grading.passed if grading else None,
                "pass_score": float(exam.pass_score),
            }
            history_items.append(item)

        return {
            "phone": phone,
            "candidate_name": candidate.display_name if candidate else None,
            "total_exams": len(history_items),
            "completed_exams": len([r for r in history_items if r["record_status"] in ("submitted", "graded")]),
            "passed_exams": len([r for r in history_items if r["passed"] is True]),
            "failed_exams": len([r for r in history_items if r["passed"] is False]),
            "history": history_items,
        }

    def get_exams_statistics_list(
        self,
        current_user: User,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取多个考试的统计数据列表

        Args:
            current_user: 当前用户
            status: 考试状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 考试统计列表
        """
        # 1. 查询考试列表（遵循数据隔离）
        query = self.db.query(Exam)
        if current_user.role != "admin":
            query = query.filter(Exam.created_by == current_user.id)
        if status:
            query = query.filter(Exam.status == status)

        total = query.count()
        exams = query.order_by(Exam.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        # 2. 计算每个考试的统计
        items = []
        for exam in exams:
            try:
                stats = self.get_exam_statistics(exam.id, current_user)
                items.append(stats)
            except Exception as e:
                logger.warning(f"获取考试 {exam.id} 统计失败: {e}")
                items.append({
                    "exam_id": exam.id,
                    "exam_title": exam.title,
                    "exam_status": exam.status,
                    "error": str(e),
                })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ============================================================
    # S4.4-B 数据查询接口
    # ============================================================

    def get_exam_analysis(
        self,
        exam_id: int,
        current_user: User,
    ) -> dict:
        """获取考试完整分析数据

        包含：
        - 基础信息（名称、状态、创建时间、发布时间）
        - 统计信息（复用 get_exam_statistics）
        - 答题概况（总题数、总分、平均得分率）

        Args:
            exam_id: 考试 ID
            current_user: 当前用户

        Returns:
            dict: 考试分析数据
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        self._check_view_permission(exam, current_user)

        # 1. 基础信息
        result = {
            "exam_id": exam.id,
            "exam_title": exam.title,
            "exam_status": exam.status,
            "exam_position": exam.position,
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
            "published_at": exam.published_at.isoformat() if exam.published_at else None,
            "duration_minutes": exam.duration_minutes,
            "pass_score": float(exam.pass_score),
        }

        # 2. 统计信息（复用已有方法）
        stats = self.get_exam_statistics(exam_id=exam_id, current_user=current_user)
        result["statistics"] = stats

        # 3. 答题概况
        questions = self.db.query(Question).filter(Question.exam_id == exam_id).all()
        total_questions = len(questions)
        total_score = sum(float(q.score) for q in questions)

        # 计算平均得分率
        answer_records = self.db.query(AnswerRecord).join(
            ExamRecord, AnswerRecord.exam_record_id == ExamRecord.id
        ).filter(
            ExamRecord.exam_id == exam_id,
            ExamRecord.status.in_(["submitted", "graded"]),
        ).all()

        answered_count = len(answer_records)
        scored_answers = [a for a in answer_records if a.score is not None]
        total_earned = sum(float(a.score) for a in scored_answers) if scored_answers else 0

        avg_score_rate = None
        if total_score > 0 and scored_answers:
            max_possible = total_score * len(set(a.exam_record_id for a in scored_answers))
            if max_possible > 0:
                avg_score_rate = round(total_earned / max_possible * 100, 1)

        result["answer_overview"] = {
            "total_questions": total_questions,
            "total_score": total_score,
            "answered_count": answered_count,
            "avg_score_rate": avg_score_rate,
        }

        return result

    def get_exam_results(
        self,
        exam_id: int,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取考试成绩列表（分页）

        返回每个参与人员的成绩信息，支持分页避免大量数据返回

        Args:
            exam_id: 考试 ID
            current_user: 当前用户
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 成绩列表数据
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        self._check_view_permission(exam, current_user)

        pass_score = float(exam.pass_score)

        # 分页查询考试记录
        query = self.db.query(ExamRecord).filter(ExamRecord.exam_id == exam_id)
        total = query.count()
        records = query.order_by(ExamRecord.submitted_at.desc().nullslast()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        items = []
        for record in records:
            grading = self.db.query(GradingRecord).filter(
                GradingRecord.exam_record_id == record.id
            ).first()

            score = None
            passed = None
            if grading and grading.total_score is not None:
                score = float(grading.total_score)
                passed = grading.passed
            elif record.score is not None:
                score = float(record.score)

            if passed is None and score is not None:
                passed = score >= pass_score

            item = {
                "record_id": record.id,
                "candidate_name": record.candidate_name,
                "candidate_phone": record.candidate_phone,
                "candidate_email": record.candidate_email,
                "status": record.status,
                "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "score": score,
                "passed": passed,
            }
            items.append(item)

        return {
            "exam_id": exam_id,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_candidate_exam_history_paginated(
        self,
        candidate_id: int,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: str | None = None,
    ) -> dict:
        """获取候选人历史考试记录（增强版：分页/排序/过滤）

        Args:
            candidate_id: 候选人 ID
            current_user: 当前用户
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段（created_at / submitted_at / score）
            sort_order: 排序方向（asc / desc）
            status: 状态筛选

        Returns:
            dict: 分页的历史考试记录
        """
        candidate = self.db.query(User).filter(User.id == candidate_id).first()
        if not candidate:
            raise NotFoundException("候选人不存在")

        self._check_candidate_history_permission(candidate_id, current_user)

        # 构建查询
        query = self.db.query(ExamRecord).filter(
            ExamRecord.candidate_phone == candidate.phone,
        )

        # 状态过滤
        if status:
            query = query.filter(ExamRecord.status == status)

        # 排序
        sort_column = {
            "created_at": ExamRecord.created_at,
            "submitted_at": ExamRecord.submitted_at,
        }.get(sort_by, ExamRecord.created_at)

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        # 构建历史记录
        history_items = []
        for record in records:
            exam = self.db.query(Exam).filter(Exam.id == record.exam_id).first()
            if not exam:
                continue

            grading = self.db.query(GradingRecord).filter(
                GradingRecord.exam_record_id == record.id
            ).first()

            score = None
            if grading and grading.total_score:
                score = float(grading.total_score)
            elif record.score:
                score = float(record.score)

            item = {
                "exam_record_id": record.id,
                "exam_id": exam.id,
                "exam_title": exam.title,
                "exam_position": exam.position,
                "exam_status": exam.status,
                "record_status": record.status,
                "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "score": score,
                "passed": grading.passed if grading else None,
                "pass_score": float(exam.pass_score),
            }
            history_items.append(item)

        return {
            "candidate_id": candidate_id,
            "candidate_name": candidate.display_name or candidate.username,
            "total": total,
            "page": page,
            "page_size": page_size,
            "history": history_items,
        }

    def get_record_answers(
        self,
        exam_id: int,
        record_id: int,
        current_user: User,
    ) -> dict:
        """获取一次考试的答题详情

        返回每道题的：题目、用户答案、标准答案、得分、评分状态

        Args:
            exam_id: 考试 ID
            record_id: 考试记录 ID
            current_user: 当前用户

        Returns:
            dict: 答题详情数据
        """
        # 1. 获取考试记录
        record = self.db.query(ExamRecord).filter(
            ExamRecord.id == record_id,
            ExamRecord.exam_id == exam_id,
        ).first()
        if not record:
            raise NotFoundException("考试记录不存在")

        # 2. 权限校验
        self._check_record_answers_permission(record, current_user)

        # 3. 获取答案记录
        answer_records = self.db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == record_id,
        ).order_by(AnswerRecord.id.asc()).all()

        # 4. 构建答题详情
        answers = []
        for ar in answer_records:
            # 优先使用题目快照，保证历史数据隔离
            question_data = ar.question_snapshot
            if not question_data:
                question = self.db.query(Question).filter(
                    Question.id == ar.question_id
                ).first()
                if question:
                    question_data = {
                        "id": question.id,
                        "content": question.content,
                        "type": question.type,
                        "options": question.options,
                        "answer": question.answer,
                        "score": float(question.score),
                    }

            if not question_data:
                continue

            # 确定评分状态
            grading_status = "pending"
            if ar.score is not None and ar.is_correct is not None:
                grading_status = "graded"
            elif ar.ai_score is not None:
                grading_status = "ai_graded"
            elif ar.needs_review:
                grading_status = "needs_review"

            answer_item = {
                "answer_id": ar.id,
                "question_id": ar.question_id,
                "question_content": question_data.get("content", ""),
                "question_type": question_data.get("type", ""),
                "question_score": float(question_data.get("score", 0)),
                "user_answer": ar.answer_content,
                "standard_answer": question_data.get("answer", ""),
                "score": float(ar.score) if ar.score is not None else None,
                "is_correct": ar.is_correct,
                "grading_status": grading_status,
                "ai_score": float(ar.ai_score) if ar.ai_score is not None else None,
                "ai_comment": ar.ai_comment,
            }
            answers.append(answer_item)

        # 汇总
        total_score = sum(a["question_score"] for a in answers)
        earned_score = sum(a["score"] for a in answers if a["score"] is not None)
        completed_questions = len([a for a in answers if a["score"] is not None])
        total_questions = len(answers)

        return {
            "exam_id": exam_id,
            "record_id": record_id,
            "candidate_name": record.candidate_name,
            "exam_status": record.status,
            "total_questions": total_questions,
            "completed_questions": completed_questions,
            "total_score": total_score,
            "earned_score": earned_score,
            "answers": answers,
        }

    def _check_record_answers_permission(
        self, record: ExamRecord, current_user: User
    ) -> None:
        """检查查看答题详情的权限

        规则：
        - admin: 可查看所有
        - hr: 只能查看自己管理范围内的考试记录
        - employee/candidate: 只能查看自己的答题记录（通过手机号匹配）
        """
        if current_user.role == "admin":
            return

        if current_user.role in ("employee", "candidate"):
            if record.candidate_phone != current_user.phone:
                raise ForbiddenException("无权查看他人的答题记录")
            return

        if current_user.role == "hr":
            exam = self.db.query(Exam).filter(Exam.id == record.exam_id).first()
            if exam and exam.created_by == current_user.id:
                return
            raise ForbiddenException("无权查看此考试的答题记录")

        raise ForbiddenException("无权限访问")

    def _check_view_permission(self, exam: Exam, current_user: User) -> None:
        """检查查看考试统计的权限

        规则：
        - admin: 可查看所有
        - hr: 只能查看自己创建的考试
        - employee/candidate: 禁止访问
        """
        if current_user.role == "admin":
            return

        if current_user.role in ("employee", "candidate"):
            raise ForbiddenException("候选人无权访问考试统计")

        if exam.created_by != current_user.id:
            raise ForbiddenException("无权查看此考试的统计数据")

    def _check_candidate_history_permission(
        self, candidate_id: int, current_user: User
    ) -> None:
        """检查查看候选人历史的权限

        规则：
        - admin: 可查看所有
        - hr: 可查看所有
        - employee: 只能查看自己的
        """
        if current_user.role in ("admin", "hr"):
            return

        if current_user.role in ("employee", "candidate"):
            if current_user.id != candidate_id:
                raise ForbiddenException("无权查看其他候选人的历史记录")
            return

        raise ForbiddenException("无权限访问")

    def _check_hr_or_admin(self, current_user: User) -> None:
        """检查是否为 HR 或 Admin"""
        if current_user.role not in ("hr", "admin"):
            raise ForbiddenException("需要 HR 或管理员权限")
