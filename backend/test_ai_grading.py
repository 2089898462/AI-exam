"""
S5.3 AI 智能阅卷 MVP 测试
覆盖：AI 评分 Service、评分记录、权限控制、异常处理、完整流程
"""
import json
import sys
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 创建内存数据库
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 加载模型
from app.db.base import Base
from app.models.answer_record import AnswerRecord
from app.models.ai_score_record import AIScoreRecord
from app.models.exam import Exam
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.models.user import User
from app.services.ai_grading_service import AIGradingService
from app.exceptions import BusinessException, NotFoundException

Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 全局计数器，用于生成唯一测试数据
_test_counter = 0


def _next_id():
    global _test_counter
    _test_counter += 1
    return _test_counter


def create_test_data(db, suffix=None):
    """创建测试数据"""
    if suffix is None:
        suffix = str(_next_id())
    else:
        suffix = str(suffix)

    user = User(
        username=f"hr_test_{suffix}",
        email=f"hr_{suffix}@test.com",
        password_hash="test",
        display_name=f"HR Test {suffix}",
        role="hr",
    )
    db.add(user)
    db.flush()

    exam = Exam(
        title=f"AI 阅卷测试考试 {suffix}",
        description="测试用",
        duration_minutes=60,
        pass_score=60.0,
        status="published",
        created_by=user.id,
    )
    db.add(exam)
    db.flush()

    question = Question(
        exam_id=exam.id,
        type="short_answer",
        content="请简述面向对象编程的三大特性。",
        answer="封装、继承、多态",
        score=10.0,
        sort_order=1,
    )
    db.add(question)
    db.flush()

    exam_record = ExamRecord(
        exam_id=exam.id,
        candidate_name="测试候选人",
        candidate_email="candidate@test.com",
        status="submitted",
    )
    db.add(exam_record)
    db.flush()

    answer = AnswerRecord(
        exam_record_id=exam_record.id,
        question_id=question.id,
        answer_content="面向对象的三大特性包括封装和继承。",
    )
    db.add(answer)
    db.commit()
    db.refresh(user)
    db.refresh(answer)
    return user, answer, question, exam_record, exam


def create_empty_answer_data(db, suffix=None):
    """创建空答案测试数据"""
    if suffix is None:
        suffix = str(_next_id())
    else:
        suffix = str(suffix)

    user = User(
        username=f"hr_empty_{suffix}",
        email=f"hr_empty_{suffix}@test.com",
        password_hash="test",
        display_name=f"HR Empty {suffix}",
        role="hr",
    )
    db.add(user)
    db.flush()

    exam = Exam(
        title=f"空答案测试 {suffix}",
        description="测试用",
        duration_minutes=30,
        pass_score=60.0,
        status="published",
        created_by=user.id,
    )
    db.add(exam)
    db.flush()

    question = Question(
        exam_id=exam.id,
        type="short_answer",
        content="什么是机器学习？",
        answer="机器学习是人工智能的一个分支",
        score=5.0,
        sort_order=1,
    )
    db.add(question)
    db.flush()

    exam_record = ExamRecord(
        exam_id=exam.id,
        candidate_name="空答案候选人",
        candidate_email="empty@test.com",
        status="submitted",
    )
    db.add(exam_record)
    db.flush()

    answer = AnswerRecord(
        exam_record_id=exam_record.id,
        question_id=question.id,
        answer_content=None,
    )
    db.add(answer)
    db.commit()
    db.refresh(user)
    db.refresh(answer)
    return user, answer


def test_ai_grading_service_exists():
    """1.1 AIGradingService 存在且可实例化"""
    db = SessionLocal()
    try:
        service = AIGradingService(db)
        assert service is not None
        print("[PASS] 1.1 AIGradingService 实例化")
    finally:
        db.close()


def test_trigger_ai_scoring_with_valid_data():
    """1.2 触发 AI 评分 - 正常流程（Mock AI Service）"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "答案提到了封装和继承，但未提及多态，整体回答基本正确。",
            "matched_points": ["封装", "继承"],
            "missing_points": ["多态"],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            record = service.trigger_ai_scoring(answer.id)

            assert record is not None
            assert record.ai_score == 7.0
            assert record.max_score == 10.0
            assert record.review_status == "ai_scored"
            assert record.confidence == 0.85
            assert record.prompt_version == "v2"
            assert record.model_name == "deepseek-chat"
            assert record.reviewed_by is None
            assert record.reviewed_at is None

            # 验证 matched_points 和 missing_points 存储
            matched = json.loads(record.matched_points)
            missing = json.loads(record.missing_points)
            assert "封装" in matched
            assert "多态" in missing

        print("[PASS] 1.2 触发 AI 评分 - 正常流程")
    finally:
        db.close()


def test_trigger_ai_scoring_empty_answer():
    """1.3 触发 AI 评分 - 空答案快速处理"""
    db = SessionLocal()
    try:
        user, answer = create_empty_answer_data(db)
        service = AIGradingService(db)

        record = service.trigger_ai_scoring(answer.id)

        assert record.ai_score == 0.0
        assert record.review_status == "ai_scored"
        assert record.confidence == 1.0
        assert record.score_reason == "候选人未作答，AI 建议 0 分"

        missing = json.loads(record.missing_points)
        assert "全部要点" in missing

        print("[PASS] 1.3 触发 AI 评分 - 空答案快速处理")
    finally:
        db.close()


def test_trigger_ai_scoring_not_found():
    """1.4 触发 AI 评分 - 答题记录不存在"""
    db = SessionLocal()
    try:
        service = AIGradingService(db)
        try:
            service.trigger_ai_scoring(99999)
            assert False, "应抛出 NotFoundException"
        except NotFoundException as e:
            assert "答题记录不存在" in str(e)
        print("[PASS] 1.4 触发 AI 评分 - 答题记录不存在")
    finally:
        db.close()


def test_trigger_ai_scoring_duplicate():
    """1.5 触发 AI 评分 - 重复评分拒绝"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 8.0,
            "reason": "测试",
            "matched_points": ["封装"],
            "missing_points": [],
            "confidence": 0.9,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

            try:
                service.trigger_ai_scoring(answer.id)
                assert False, "应抛出 BusinessException"
            except BusinessException as e:
                assert "已存在 AI 评分记录" in str(e)

        print("[PASS] 1.5 触发 AI 评分 - 重复评分拒绝")
    finally:
        db.close()


def test_get_ai_scoring_result():
    """2.1 查询 AI 评分结果"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "答案提到了封装和继承，但未提及多态。",
            "matched_points": ["封装", "继承"],
            "missing_points": ["多态"],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        result = service.get_ai_scoring_result(answer.id)

        assert result["answer_record_id"] == answer.id
        assert result["ai_score"] == 7.0
        assert result["max_score"] == 10.0
        assert "封装" in result["matched_points"]
        assert "多态" in result["missing_points"]
        assert result["confidence"] == 0.85
        assert result["needs_review"] == False
        assert result["review_status"] == "ai_scored"
        assert result["question_content"] == question.content
        assert result["candidate_answer"] == answer.answer_content

        print("[PASS] 2.1 查询 AI 评分结果")
    finally:
        db.close()


def test_get_ai_scoring_result_not_found():
    """2.2 查询 AI 评分结果 - 无记录"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        try:
            service.get_ai_scoring_result(answer.id)
            assert False, "应抛出 BusinessException"
        except BusinessException as e:
            assert "尚无 AI 评分" in str(e)

        print("[PASS] 2.2 查询 AI 评分结果 - 无记录")
    finally:
        db.close()


def test_confirm_ai_scoring():
    """3.1 HR 确认 AI 评分"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "答案提到了封装和继承，但未提及多态。",
            "matched_points": ["封装", "继承"],
            "missing_points": ["多态"],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        # HR 确认评分
        confirmed = service.confirm_ai_scoring(
            answer_record_id=answer.id,
            confirmed_score=7.5,
            reviewer_id=user.id,
            hr_remark="补充了部分知识点，调整为 7.5 分",
        )

        assert confirmed.review_status == "completed"
        assert confirmed.confirmed_score == 7.5
        assert confirmed.reviewed_by == user.id
        assert confirmed.hr_remark == "补充了部分知识点，调整为 7.5 分"
        assert confirmed.reviewed_at is not None

        # 验证 AnswerRecord.score 已更新
        db.refresh(answer)
        assert float(answer.score) == 7.5
        assert float(answer.ai_score) == 7.0
        assert answer.is_correct == True

        print("[PASS] 3.1 HR 确认 AI 评分")
    finally:
        db.close()


def test_confirm_ai_scoring_invalid_range():
    """3.2 HR 确认 AI 评分 - 分数超范围"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "测试",
            "matched_points": [],
            "missing_points": [],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        # 分数超限
        try:
            service.confirm_ai_scoring(
                answer_record_id=answer.id,
                confirmed_score=15.0,
                reviewer_id=user.id,
            )
            assert False, "应抛出 BusinessException"
        except BusinessException as e:
            assert "0 ~ 10" in str(e)

        # 负分
        try:
            service.confirm_ai_scoring(
                answer_record_id=answer.id,
                confirmed_score=-1.0,
                reviewer_id=user.id,
            )
            assert False, "应抛出 BusinessException"
        except BusinessException as e:
            assert "0 ~ 10" in str(e)

        print("[PASS] 3.2 HR 确认 AI 评分 - 分数超范围")
    finally:
        db.close()


def test_reject_ai_scoring():
    """3.3 HR 拒绝 AI 评分"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "测试",
            "matched_points": [],
            "missing_points": [],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        rejected = service.reject_ai_scoring(
            answer_record_id=answer.id,
            reviewer_id=user.id,
            hr_remark="评分不准确，需要重新评分",
        )

        assert rejected.review_status == "rejected"
        assert rejected.reviewed_by == user.id
        assert rejected.hr_remark == "评分不准确，需要重新评分"

        # 拒绝后可以重新触发（更新原记录而非新建）
        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai2:
            mock_ai2.evaluate_scoring.return_value = mock_result
            new_record = service.trigger_ai_scoring(answer.id)
            assert new_record.review_status == "ai_scored"
            # 被拒绝后重新评分，更新原记录（ID 相同）
            assert new_record.id == rejected.id

        print("[PASS] 3.3 HR 拒绝 AI 评分")
    finally:
        db.close()


def test_get_ai_scoring_status():
    """4.1 查询 AI 评分状态"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        # 初始状态
        status = service.get_ai_scoring_status(answer.id)
        assert status["has_ai_score"] == False
        assert status["review_status"] is None

        # 触发评分后
        mock_result = {
            "score": 7.0,
            "reason": "测试",
            "matched_points": [],
            "missing_points": [],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }
        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        status = service.get_ai_scoring_status(answer.id)
        assert status["has_ai_score"] == True
        assert status["review_status"] == "ai_scored"
        assert status["ai_score"] == 7.0

        # 确认后
        service.confirm_ai_scoring(answer.id, 7.0, user.id)
        status = service.get_ai_scoring_status(answer.id)
        assert status["review_status"] == "completed"
        assert status["confirmed_score"] == 7.0

        print("[PASS] 4.1 查询 AI 评分状态")
    finally:
        db.close()


def test_get_pending_ai_scores():
    """4.2 获取待审核 AI 评分列表"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        # 空列表
        result = service.get_pending_ai_scores()
        assert result["total"] == 0
        assert len(result["items"]) == 0

        # 触发评分
        mock_result = {
            "score": 7.0,
            "reason": "测试",
            "matched_points": ["封装"],
            "missing_points": ["多态"],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }
        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        result = service.get_pending_ai_scores()
        assert result["total"] == 1
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["ai_score"] == 7.0
        assert item["review_status"] == "ai_scored"
        assert "封装" in item["matched_points"]
        assert "多态" in item["missing_points"]

        # 按状态筛选
        result = service.get_pending_ai_scores(status="ai_scored")
        assert result["total"] == 1

        result = service.get_pending_ai_scores(status="completed")
        assert result["total"] == 0

        print("[PASS] 4.2 获取待审核 AI 评分列表")
    finally:
        db.close()


def test_ai_scoring_service_mock():
    """5.1 AI Scoring Service Mock 调用测试"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = {
                "score": 8.5,
                "reason": "非常好，覆盖了主要知识点",
                "matched_points": ["封装", "继承", "多态"],
                "missing_points": [],
                "confidence": 0.95,
                "prompt_version": "v2",
                "needs_review": False,
            }

            record = service.trigger_ai_scoring(answer.id)

            # 验证调用参数
            call_args = mock_ai.evaluate_scoring.call_args
            assert call_args[1]["question"] == question.content
            assert call_args[1]["standard_answer"] == question.answer
            assert call_args[1]["user_answer"] == answer.answer_content
            assert call_args[1]["max_score"] == 10.0
            assert call_args[1]["prompt_version"] == "v2"

            # 验证结果
            assert record.ai_score == 8.5
            assert record.confidence == 0.95

        print("[PASS] 5.1 AI Scoring Service Mock 调用测试")
    finally:
        db.close()


def test_ai_scoring_service_failure():
    """5.2 AI 评分服务失败 - 降级处理"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        from app.exceptions import BusinessException
        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.side_effect = BusinessException(
                "AI 服务不可用", error_code="AI_SERVICE_UNAVAILABLE"
            )

            record = service.trigger_ai_scoring(answer.id)

            # 失败时降级处理，仍创建记录
            assert record is not None
            assert record.ai_score == 0.0
            assert record.review_status == "ai_scored"
            assert "AI 评分服务异常" in record.score_reason
            assert record.confidence == 0.0

        print("[PASS] 5.2 AI 评分服务失败 - 降级处理")
    finally:
        db.close()


def test_only_short_answer_supported():
    """5.3 只支持简答题类型"""
    db = SessionLocal()
    try:
        # 创建选择题
        suffix = _next_id()
        user = User(
            username=f"hr_mcq_{suffix}",
            email=f"mcq_{suffix}@test.com",
            password_hash="test",
            display_name=f"HR MCQ {suffix}",
            role="hr",
        )
        db.add(user)
        db.flush()

        exam = Exam(
            title="选择题测试",
            description="测试用",
            duration_minutes=30,
            pass_score=60.0,
            status="published",
            created_by=user.id,
        )
        db.add(exam)
        db.flush()

        question = Question(
            exam_id=exam.id,
            type="single_choice",
            content="以下哪个是编程语言？",
            answer="A",
            score=5.0,
            sort_order=1,
        )
        db.add(question)
        db.flush()

        exam_record = ExamRecord(
            exam_id=exam.id,
            candidate_name="选择题候选人",
            candidate_email="mcq@test.com",
            status="submitted",
        )
        db.add(exam_record)
        db.flush()

        answer = AnswerRecord(
            exam_record_id=exam_record.id,
            question_id=question.id,
            answer_content="A",
        )
        db.add(answer)
        db.commit()

        service = AIGradingService(db)

        try:
            service.trigger_ai_scoring(answer.id)
            assert False, "应抛出 BusinessException"
        except BusinessException as e:
            assert "简答题" in str(e)

        print("[PASS] 5.3 只支持简答题类型")
    finally:
        db.close()


def test_complete_flow_submit_score_confirm():
    """6.1 完整流程：提交 → AI 评分 → HR 确认 → 最终成绩"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        # Step 1: 初始状态
        status = service.get_ai_scoring_status(answer.id)
        assert status["has_ai_score"] == False
        print("  Step 1: 初始状态 - 无 AI 评分")

        # Step 2: 触发 AI 评分
        mock_result = {
            "score": 7.0,
            "reason": "答案完整，覆盖了主要知识点，但缺少多态的说明。",
            "matched_points": ["封装", "继承"],
            "missing_points": ["多态"],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }
        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            record = service.trigger_ai_scoring(answer.id)

        assert record.review_status == "ai_scored"
        assert record.ai_score == 7.0
        print("  Step 2: AI 评分已生成")

        # Step 3: 查询评分结果
        result = service.get_ai_scoring_result(answer.id)
        assert result["ai_score"] == 7.0
        assert "封装" in result["matched_points"]
        print("  Step 3: 查询评分结果")

        # Step 4: HR 确认评分
        confirmed = service.confirm_ai_scoring(
            answer_record_id=answer.id,
            confirmed_score=7.0,
            reviewer_id=user.id,
            hr_remark="确认 AI 评分",
        )
        assert confirmed.review_status == "completed"
        print("  Step 4: HR 确认评分")

        # Step 5: 验证最终成绩
        db.refresh(answer)
        assert float(answer.score) == 7.0
        assert answer.is_correct == True
        status = service.get_ai_scoring_status(answer.id)
        assert status["review_status"] == "completed"
        assert status["confirmed_score"] == 7.0
        print("  Step 5: 最终成绩已更新")

        print("[PASS] 6.1 完整流程：提交 → AI 评分 → HR 确认 → 最终成绩")
    finally:
        db.close()


def test_ai_score_record_model_fields():
    """7.1 AIScoreRecord 模型字段完整性"""
    db = SessionLocal()
    try:
        # 验证模型字段
        columns = AIScoreRecord.__table__.columns.keys()
        required_fields = [
            "id", "answer_record_id", "ai_score", "max_score",
            "score_reason", "matched_points", "missing_points",
            "confidence", "model_name", "prompt_version",
            "review_status", "reviewed_by", "reviewed_at",
            "hr_remark", "confirmed_score",
            "created_at", "updated_at",
        ]
        for field in required_fields:
            assert field in columns, f"缺少字段: {field}"

        print("[PASS] 7.1 AIScoreRecord 模型字段完整性")
    finally:
        db.close()


def test_review_status_transitions():
    """7.2 审核状态流转"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 7.0,
            "reason": "测试",
            "matched_points": [],
            "missing_points": [],
            "confidence": 0.85,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result

            # pending → ai_scored
            record = service.trigger_ai_scoring(answer.id)
            assert record.review_status == "ai_scored"

            # ai_scored → completed (通过 confirm)
            confirmed = service.confirm_ai_scoring(answer.id, 7.0, user.id)
            assert confirmed.review_status == "completed"

        # 重新评分测试 rejected → ai_scored
        # 创建新问题和新答案（避免唯一约束冲突）
        question2 = Question(
            exam_id=exam_record.exam_id,
            type="short_answer",
            content="另一个题目",
            answer="答案 B",
            score=5.0,
            sort_order=2,
        )
        db.add(question2)
        db.flush()

        answer2 = AnswerRecord(
            exam_record_id=exam_record.id,
            question_id=question2.id,
            answer_content="另一个答案",
        )
        db.add(answer2)
        db.commit()

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai2:
            mock_ai2.evaluate_scoring.return_value = mock_result
            r2 = service.trigger_ai_scoring(answer2.id)
            assert r2.review_status == "ai_scored"

            # ai_scored → rejected
            rejected = service.reject_ai_scoring(answer2.id, user.id, "不准确")
            assert rejected.review_status == "rejected"

            # rejected → ai_scored (重新触发)
            r3 = service.trigger_ai_scoring(answer2.id)
            assert r3.review_status == "ai_scored"

        print("[PASS] 7.2 审核状态流转")
    finally:
        db.close()


def test_low_confidence_needs_review():
    """7.3 低置信度标记"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        mock_result = {
            "score": 3.0,
            "reason": "答案不完整",
            "matched_points": [],
            "missing_points": ["封装", "继承", "多态"],
            "confidence": 0.4,  # 低置信度
            "prompt_version": "v2",
            "needs_review": True,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            record = service.trigger_ai_scoring(answer.id)

        result = service.get_ai_scoring_result(answer.id)
        assert result["needs_review"] == True
        assert result["confidence"] == 0.4

        print("[PASS] 7.3 低置信度标记")
    finally:
        db.close()


def test_ai_does_not_modify_score_directly():
    """8.1 AI 评分不直接修改最终成绩（需 HR 确认）"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        # AI 评分前，score 为 None
        assert answer.score is None

        mock_result = {
            "score": 8.0,
            "reason": "测试",
            "matched_points": [],
            "missing_points": [],
            "confidence": 0.9,
            "prompt_version": "v2",
            "needs_review": False,
        }

        with patch("app.services.ai_grading_service.ai_scoring_service") as mock_ai:
            mock_ai.evaluate_scoring.return_value = mock_result
            service.trigger_ai_scoring(answer.id)

        # AI 评分后，AnswerRecord.score 仍为 None（未确认前不修改）
        db.refresh(answer)
        assert answer.score is None

        # HR 确认后才更新
        service.confirm_ai_scoring(answer.id, 8.0, user.id)
        db.refresh(answer)
        assert float(answer.score) == 8.0

        print("[PASS] 8.1 AI 评分不直接修改最终成绩")
    finally:
        db.close()


def test_confirm_invalid_status():
    """8.2 非 ai_scored 状态无法确认"""
    db = SessionLocal()
    try:
        user, answer, question, exam_record, exam = create_test_data(db)
        service = AIGradingService(db)

        # 没有评分记录时
        try:
            service.confirm_ai_scoring(answer.id, 5.0, user.id)
            assert False
        except BusinessException as e:
            assert "不存在" in str(e) or "无法确认" in str(e)

        print("[PASS] 8.2 非 ai_scored 状态无法确认")
    finally:
        db.close()


def main():
    print("=" * 70)
    print("S5.3 AI 智能阅卷 MVP 测试")
    print("=" * 70)

    tests = [
        ("1.1 AIGradingService 实例化", test_ai_grading_service_exists),
        ("1.2 触发 AI 评分 - 正常流程", test_trigger_ai_scoring_with_valid_data),
        ("1.3 触发 AI 评分 - 空答案处理", test_trigger_ai_scoring_empty_answer),
        ("1.4 触发 AI 评分 - 记录不存在", test_trigger_ai_scoring_not_found),
        ("1.5 触发 AI 评分 - 重复拒绝", test_trigger_ai_scoring_duplicate),
        ("2.1 查询 AI 评分结果", test_get_ai_scoring_result),
        ("2.2 查询 AI 评分结果 - 无记录", test_get_ai_scoring_result_not_found),
        ("3.1 HR 确认 AI 评分", test_confirm_ai_scoring),
        ("3.2 HR 确认 AI 评分 - 分数超范围", test_confirm_ai_scoring_invalid_range),
        ("3.3 HR 拒绝 AI 评分", test_reject_ai_scoring),
        ("4.1 查询 AI 评分状态", test_get_ai_scoring_status),
        ("4.2 获取待审核列表", test_get_ai_scoring_status),
        ("5.1 AI Service Mock 调用", test_ai_scoring_service_mock),
        ("5.2 AI Service 失败降级", test_ai_scoring_service_failure),
        ("5.3 只支持简答题", test_only_short_answer_supported),
        ("6.1 完整流程测试", test_complete_flow_submit_score_confirm),
        ("7.1 模型字段完整性", test_ai_score_record_model_fields),
        ("7.2 审核状态流转", test_review_status_transitions),
        ("7.3 低置信度标记", test_low_confidence_needs_review),
        ("8.1 AI 不直接修改成绩", test_ai_does_not_modify_score_directly),
        ("8.2 非 ai_scored 无法确认", test_confirm_invalid_status),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
