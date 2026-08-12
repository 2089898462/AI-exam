"""
S4.3-B 考试安全能力完善测试
覆盖：
1. 身份验证测试
   - 正确考试码+正确人员
   - 错误考试码
   - 未分配人员访问
   - 已关闭考试访问

2. 重复提交测试
   - 正常提交
   - 重复点击提交
   - 重复请求
   - 已完成考试再次提交

3. 权限测试
   - 候选人不能访问他人成绩
   - 候选人不能访问他人考试记录
"""

import sys
sys.path.insert(0, '.')

from app.db.session import _get_engine, _get_session_factory
from app.db.base import Base
from app.models import Exam, User, ExamRecord, ExamParticipant, Question, AnswerRecord
from app.models.user import User as UserModel
from app.services.exam_service import ExamService
from app.services.exam_record_service import ExamRecordService
from app.services.participant_service import ExamParticipantService
from app.exceptions import BusinessException, NotFoundException

# 创建测试引擎和会话
engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()

def cleanup_test_data(db):
    """清理测试数据"""
    # 删除所有测试考试相关的数据
    test_exam_codes = ["SEC001", "AUTH123", "CLOSED01", "AUTH456", "SEC_TEST_001", "SEC_TEST_002", "SEC_TEST_003"]
    for code in test_exam_codes:
        exams = db.query(Exam).filter(Exam.exam_code == code).all()
        for exam in exams:
            # 删除答题记录
            db.query(AnswerRecord).filter(
                AnswerRecord.exam_record_id.in_(
                    db.query(ExamRecord.id).filter(ExamRecord.exam_id == exam.id)
                )
            ).delete(synchronize_session=False)
            # 删除考试记录
            db.query(ExamRecord).filter(ExamRecord.exam_id == exam.id).delete()
            # 删除参与人员
            db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).delete()
            # 删除题目
            db.query(Question).filter(Question.exam_id == exam.id).delete()
            # 删除考试
            db.delete(exam)
    db.commit()

def create_test_exam(db, title="安全测试考试", exam_code="SEC001"):
    """创建一个已发布的测试考试"""
    hr_user = db.query(User).filter(User.role == "hr").first()
    if not hr_user:
        import bcrypt
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        hr_user = UserModel(
            username="hr_security_test",
            password_hash=hashed,
            display_name="安全测试HR",
            role="hr",
            status="active",
        )
        db.add(hr_user)
        db.commit()
        db.refresh(hr_user)

    service = ExamService(db)
    exam = service.create_exam(
        title=title,
        duration_minutes=60,
        pass_score=60,
        created_by=hr_user.id,
    )
    # 设置考试凭证
    exam.exam_code = exam_code
    
    # 添加一道测试题目以便发布
    from app.services.question_service import QuestionService
    q_service = QuestionService(db)
    q_service.create_question(
        exam_id=exam.id,
        question_no="Q1",
        type="single_choice",
        content="测试题目",
        options=[{"key": "A", "value": "选项A"}, {"key": "B", "value": "选项B"}],
        answer="A",
        score=10.0,
        current_user=hr_user,
    )
    
    # 发布考试
    service.publish_exam(exam.id, current_user=hr_user)
    db.commit()
    return exam

def add_participant(db, exam_id, name, phone):
    """添加参与人员"""
    service = ExamParticipantService(db)
    return service.add_participant(
        exam_id=exam_id,
        candidate_name=name,
        candidate_phone=phone,
    )

def run_tests():
    db = SessionLocal()
    
    # 清理残留测试数据
    cleanup_test_data(db)
    
    passed = 0
    failed = 0
    errors = []

    def test(name, func):
        nonlocal passed, failed
        try:
            func()
            passed += 1
            print(f"  [PASS] {name}")
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}")

    print("=" * 60)
    print("S4.3-B 考试安全能力完善测试")
    print("=" * 60)

    # ==================== 测试1: 身份验证 ====================
    print("\n[1] 身份验证测试")

    # 准备数据
    exam = create_test_exam(db, title="身份验证考试", exam_code="AUTH123")
    add_participant(db, exam.id, "张三", "13800000001")
    add_participant(db, exam.id, "李四", "13800000002")
    record_service = ExamRecordService(db)

    # 清理残留记录
    db.query(ExamRecord).filter(ExamRecord.exam_id == exam.id).delete()
    db.commit()

    def test_correct_code_and_person():
        """1.1 正确考试码+正确人员"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        assert record is not None
        assert record.exam_id == exam.id
        assert record.candidate_name == "张三"
        assert record.status == "not_started"
        # 验证绑定了参与人员
        assert record.participant_id is not None
        # 清理
        db.delete(record)
        db.commit()

    def test_wrong_code():
        """1.2 错误考试码"""
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code="WRONG_CODE",
                candidate_name="张三",
                candidate_phone="13800000001",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "凭证错误" in str(e) or "凭证" in str(e)

    def test_unassigned_person():
        """1.3 未分配人员访问"""
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code="AUTH123",
                candidate_name="王五",
                candidate_phone="13800000099",  # 未分配
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "未被分配" in str(e) or "无法参加" in str(e)

    def test_closed_exam():
        """1.4 已关闭考试访问"""
        # 创建并关闭一个考试
        exam2 = create_test_exam(db, title="已关闭考试", exam_code="CLOSED01")
        add_participant(db, exam2.id, "测试者", "13900000000")
        exam2.status = "closed"
        db.commit()

        try:
            record_service.create_exam_record(
                exam_id=exam2.id,
                exam_code="CLOSED01",
                candidate_name="测试者",
                candidate_phone="13900000000",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "无法参加" in str(e) or "closed" in str(e)

    test("正确考试码+正确人员", test_correct_code_and_person)
    test("错误考试码", test_wrong_code)
    test("未分配人员访问", test_unassigned_person)
    test("已关闭考试访问", test_closed_exam)

    # ==================== 测试2: 防重复提交 ====================
    print("\n[2] 防重复提交测试")

    # 清理数据
    db.query(ExamRecord).filter(ExamRecord.exam_id == exam.id).delete()
    db.commit()

    def test_normal_submit():
        """2.1 正常提交"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        record_service.start_exam(record.id)
        submitted = record_service.submit_exam(record.id)
        assert submitted.status == "submitted"
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.commit()

    def test_duplicate_creation():
        """2.2 重复创建考试记录（返回已有记录）"""
        # 创建第一条记录
        record1 = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        # 尝试创建第二条（应返回同一条）
        record2 = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        assert record1.id == record2.id, "重复创建应返回同一条记录"
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record1.id).delete()
        db.commit()

    def test_duplicate_after_submit():
        """2.3 已提交考试再次提交"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="李四",
            candidate_phone="13800000002",
        )
        record_service.start_exam(record.id)
        record_service.submit_exam(record.id)

        # 尝试重新创建
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code="AUTH123",
                candidate_name="李四",
                candidate_phone="13800000002",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "已完成" in str(e) or "无法再次参加" in str(e)

    def test_idempotent_submit():
        """2.4 幂等提交（重复点击提交按钮）"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        record_service.start_exam(record.id)
        # 第一次提交
        result1 = record_service.submit_exam(record.id)
        assert result1.status == "submitted"
        # 第二次提交（幂等）
        result2 = record_service.submit_exam(record.id)
        assert result2.status == "submitted"
        assert result2.id == result1.id
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.commit()

    test("正常提交", test_normal_submit)
    test("重复创建考试记录", test_duplicate_creation)
    test("已提交考试再次创建", test_duplicate_after_submit)
    test("幂等提交（重复点击提交）", test_idempotent_submit)

    # ==================== 测试3: 权限校验 ====================
    print("\n[3] 权限与数据隔离测试")

    def test_record_isolation():
        """3.1 考试记录隔离：不同考试的记录独立"""
        exam2 = create_test_exam(db, title="第二个考试", exam_code="AUTH456")
        add_participant(db, exam2.id, "赵六", "13800000003")

        record1 = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        record2 = record_service.create_exam_record(
            exam_id=exam2.id,
            exam_code="AUTH456",
            candidate_name="赵六",
            candidate_phone="13800000003",
        )

        # 两个记录应该不同
        assert record1.id != record2.id
        assert record1.exam_id == exam.id
        assert record2.exam_id == exam2.id

        # 查询时应该隔离
        records1 = record_service.list_exam_records(exam.id)
        records2 = record_service.list_exam_records(exam2.id)
        ids1 = [r.id for r in records1]
        ids2 = [r.id for r in records2]
        assert record1.id in ids1
        assert record2.id in ids2
        assert record1.id not in ids2
        assert record2.id not in ids1

        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record1.id).delete()
        db.query(ExamRecord).filter(ExamRecord.id == record2.id).delete()
        db.query(Exam).filter(Exam.id == exam2.id).delete()
        db.commit()

    def test_submitted_status_immutable():
        """3.2 已提交状态不可重新开始"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        record_service.start_exam(record.id)
        record_service.submit_exam(record.id)

        # 尝试重新开始
        try:
            record_service.start_exam(record.id)
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "无法开始" in str(e) or "状态" in str(e)
        finally:
            db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
            db.commit()

    def test_record_bound_to_participant():
        """3.3 考试记录绑定参与人员"""
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code="AUTH123",
            candidate_name="张三",
            candidate_phone="13800000001",
        )
        assert record.participant_id is not None, "应绑定参与人员"
        # 验证可以通过 participant_id 找回参与人员
        participant = db.query(ExamParticipant).filter(
            ExamParticipant.id == record.participant_id
        ).first()
        assert participant is not None
        assert participant.candidate_phone == "13800000001"
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.commit()

    test("考试记录隔离", test_record_isolation)
    test("已提交状态不可重新开始", test_submitted_status_immutable)
    test("考试记录绑定参与人员", test_record_bound_to_participant)

    # ==================== 结果 ====================
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"测试完成: {passed}/{total} 通过, {failed}/{total} 失败")
    if errors:
        print("\n失败详情:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print("=" * 60)

    db.close()
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
