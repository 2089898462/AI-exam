"""
S4.4-A 考试基础统计能力测试
覆盖：
1. ExamStatisticsService 统计逻辑测试
2. 权限控制测试
3. 候选人历史查询测试
"""
import sys
sys.path.insert(0, '.')

import bcrypt
from app.db.session import _get_engine, _get_session_factory
from app.db.base import Base
from app.models import Exam, User, ExamRecord, ExamParticipant, Question, AnswerRecord
from app.models.grading_record import GradingRecord
from app.services.exam_statistics_service import ExamStatisticsService
from app.services.exam_service import ExamService
from app.services.exam_record_service import ExamRecordService
from app.services.participant_service import ExamParticipantService
from app.services.question_service import QuestionService
from app.services.grading_service import GradingService
from app.exceptions import BusinessException, ForbiddenException, NotFoundException

# 创建测试引擎和会话
engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()


def cleanup_test_data(db):
    """清理所有测试数据"""
    # 先删除所有带有 S4.4-A 标记的考试相关数据
    exams = db.query(Exam).filter(Exam.title.like("%S4.4-A%")).all()
    exam_ids = [exam.id for exam in exams]
    
    if exam_ids:
        # 删除评分记录（通过考试记录ID）
        db.query(GradingRecord).filter(
            GradingRecord.exam_record_id.in_(
                db.query(ExamRecord.id).filter(ExamRecord.exam_id.in_(exam_ids))
            )
        ).delete(synchronize_session=False)
        
        # 删除答题记录
        db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id.in_(
                db.query(ExamRecord.id).filter(ExamRecord.exam_id.in_(exam_ids))
            )
        ).delete(synchronize_session=False)
        
        # 删除考试记录
        db.query(ExamRecord).filter(ExamRecord.exam_id.in_(exam_ids)).delete()
        
        # 删除参与人员
        db.query(ExamParticipant).filter(ExamParticipant.exam_id.in_(exam_ids)).delete()
        
        # 删除题目
        db.query(Question).filter(Question.exam_id.in_(exam_ids)).delete()
        
        # 删除考试
        db.query(Exam).filter(Exam.id.in_(exam_ids)).delete()
    
    # 删除测试用户相关的参与人员（手机号唯一约束可能阻止删除）
    users = db.query(User).filter(User.username.like("s4_4_a_%")).all()
    if users:
        user_phones = [u.phone for u in users if u.phone]
        if user_phones:
            # 先删除参与人员
            db.query(ExamParticipant).filter(
                ExamParticipant.candidate_phone.in_(user_phones)
            ).delete(synchronize_session=False)
    
    # 删除测试用户
    if users:
        for user in users:
            db.delete(user)
    
    db.commit()


def get_or_create_user(db, username, role, display_name=None, phone=None):
    """获取或创建测试用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        user = User(
            username=username,
            password_hash=hashed,
            display_name=display_name or username,
            role=role,
            status="active",
            phone=phone,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_test_exam(db, hr_user, title, exam_code=None, status="published", pass_score=60):
    """创建测试考试"""
    service = ExamService(db)
    exam = service.create_exam(
        title=title,
        duration_minutes=60,
        pass_score=pass_score,
        created_by=hr_user.id,
    )
    if exam_code:
        exam.exam_code = exam_code
    
    # 添加一道测试题目
    q_service = QuestionService(db)
    q_service.create_question(
        exam_id=exam.id,
        question_no="Q1",
        type="single_choice",
        content="测试题目：1+1等于几？",
        options=[{"key": "A", "value": "1"}, {"key": "B", "value": "2"}, {"key": "C", "value": "3"}, {"key": "D", "value": "4"}],
        answer="B",
        score=100.0,
        current_user=hr_user,
    )
    
    if status == "published":
        service.publish_exam(exam.id, current_user=hr_user)
    elif status == "closed":
        service.publish_exam(exam.id, current_user=hr_user)
        service.close_exam(exam.id, current_user=hr_user)
    
    db.commit()
    db.refresh(exam)
    return exam


def add_participant(db, exam_id, name, phone):
    """添加参与人员"""
    service = ExamParticipantService(db)
    return service.add_participant(
        exam_id=exam_id,
        candidate_name=name,
        candidate_phone=phone,
    )


def create_and_submit_exam_record(db, exam_id, candidate_name, candidate_phone, exam_code=None, score=None, skip_participant=False):
    """创建并提交考试记录
    
    Args:
        skip_participant: 是否跳过参与人员检查（用于无参与人员的场景）
    """
    record_service = ExamRecordService(db)
    grading_service = GradingService(db)
    
    # 如果不跳过参与人员检查，先添加参与人员
    if not skip_participant:
        # 检查是否已添加为参与人员
        existing = db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam_id,
            ExamParticipant.candidate_phone == candidate_phone
        ).first()
        if not existing:
            add_participant(db, exam_id, candidate_name, candidate_phone)
    
    # 创建考试记录
    record = record_service.create_exam_record(
        exam_id=exam_id,
        candidate_name=candidate_name,
        candidate_phone=candidate_phone,
        exam_code=exam_code,
    )
    
    # 开始考试
    record_service.start_exam(record.id)
    
    # 提交考试
    record_service.submit_exam(record.id)
    
    # 如果指定了分数，创建评分记录
    if score is not None:
        grading = GradingRecord(
            exam_record_id=record.id,
            status="completed",
            grading_type="auto",
            total_score=score,
            auto_score=score,
            passed=score >= 60,
        )
        db.add(grading)
        db.commit()
        
        # 更新考试记录分数
        record.score = score
        record.status = "graded"
        db.commit()
    
    db.refresh(record)
    return record


def run_tests():
    db = SessionLocal()
    
    # 清理残留测试数据
    cleanup_test_data(db)
    
    passed = 0
    failed = 0
    errors = []
    exam_counter = [0]

    def get_unique_code():
        """获取唯一的考试码"""
        exam_counter[0] += 1
        return f"S44A{exam_counter[0]:04d}"

    def test(name, func):
        nonlocal passed, failed
        try:
            func()
            passed += 1
            print(f"  [PASS] {name}")
        except Exception as e:
            db.rollback()
            failed += 1
            errors.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}")

    # 创建测试用户
    hr_user = get_or_create_user(db, "s4_4_a_hr", "hr", "S4.4-A HR")
    other_hr = get_or_create_user(db, "s4_4_a_other_hr", "hr", "S4.4-A Other HR")
    admin_user = get_or_create_user(db, "s4_4_a_admin", "admin", "S4.4-A Admin")
    candidate_user = get_or_create_user(db, "s4_4_a_candidate", "employee", "S4.4-A Candidate", phone="13900000000")
    
    stats_service = ExamStatisticsService(db)

    print("=" * 70)
    print("S4.4-A 考试基础统计能力测试")
    print("=" * 70)

    # ==================== 测试1: 考试统计 Service 测试 ====================
    print("\n[1] 考试统计 Service 测试")

    def test_normal_exam_statistics():
        """1.1 正常考试统计"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-A 正常统计测试", exam_code=code)
        
        # 记录当前考试ID用于后续验证
        exam_id = exam.id
        
        # 添加参与人员
        p1 = add_participant(db, exam_id, "张三", "13800000001")
        p2 = add_participant(db, exam_id, "李四", "13800000002")
        p3 = add_participant(db, exam_id, "王五", "13800000003")
        
        # 提交两个人的考试（一个通过，一个不通过）
        create_and_submit_exam_record(db, exam_id, "张三", "13800000001", exam_code=code, score=80)
        create_and_submit_exam_record(db, exam_id, "李四", "13800000002", exam_code=code, score=45)
        
        # 获取统计
        stats = stats_service.get_exam_statistics(exam_id, hr_user)
        
        assert stats["total_participants"] == 3, f"参与人数应为3，实际为{stats['total_participants']}"
        assert stats["completed_count"] == 2, f"已完成人数应为2，实际为{stats['completed_count']}"
        assert stats["unfinished_count"] == 1, f"未完成人数应为1，实际为{stats['unfinished_count']}"
        assert stats["average_score"] == 62.5, f"平均分应为62.5，实际为{stats['average_score']}"
        assert stats["max_score"] == 80.0, f"最高分应为80，实际为{stats['max_score']}"
        assert stats["min_score"] == 45.0, f"最低分应为45，实际为{stats['min_score']}"
        assert stats["pass_count"] == 1, f"通过人数应为1，实际为{stats['pass_count']}"
        assert stats["pass_rate"] == 50.0, f"通过率应为50%，实际为{stats['pass_rate']}"

    def test_no_participants():
        """1.2 无参与人员的考试统计"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-A 无参与测试", exam_code=code)
        
        stats = stats_service.get_exam_statistics(exam.id, hr_user)
        
        assert stats["total_participants"] == 0, "参与人数应为0"
        assert stats["completed_count"] == 0, "已完成人数应为0"
        assert stats["average_score"] is None, "平均分应为None"
        assert stats["max_score"] is None, "最高分应为None"
        assert stats["pass_count"] == 0, "通过人数应为0"
        assert stats["pass_rate"] is None, "通过率应为None"

    def test_no_score_records():
        """1.3 有提交但无成绩的考试统计"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-A 无成绩测试", exam_code=code)
        
        add_participant(db, exam.id, "测试人员", "13800000999")
        # 提交但不评分
        create_and_submit_exam_record(db, exam.id, "测试人员", "13800000999", exam_code=code)
        
        stats = stats_service.get_exam_statistics(exam.id, hr_user)
        
        assert stats["total_participants"] == 1, "参与人数应为1"
        assert stats["completed_count"] == 1, "已完成人数应为1"
        assert stats["average_score"] is None, "无成绩时平均分应为None"

    def test_multi_score_statistics():
        """1.4 多人考试成绩计算"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-A 多人统计测试", exam_code=code)
        
        # 添加5个参与人员
        phones = ["13811110001", "13811110002", "13811110003", "13811110004", "13811110005"]
        scores = [70, 85, 55, 90, 60]  # 4人通过，1人不通过
        names = ["人员A", "人员B", "人员C", "人员D", "人员E"]
        
        for i, phone in enumerate(phones):
            add_participant(db, exam.id, names[i], phone)
            create_and_submit_exam_record(db, exam.id, names[i], phone, exam_code=code, score=scores[i])
        
        stats = stats_service.get_exam_statistics(exam.id, hr_user)
        
        assert stats["total_participants"] == 5, f"参与人数应为5，实际为{stats['total_participants']}"
        assert stats["completed_count"] == 5, f"已完成人数应为5，实际为{stats['completed_count']}"
        assert stats["average_score"] == 72.0, f"平均分应为72，实际为{stats['average_score']}"
        assert stats["max_score"] == 90.0, f"最高分应为90，实际为{stats['max_score']}"
        assert stats["min_score"] == 55.0, f"最低分应为55，实际为{stats['min_score']}"
        assert stats["pass_count"] == 4, f"通过人数应为4，实际为{stats['pass_count']}"
        assert stats["pass_rate"] == 80.0, f"通过率应为80%，实际为{stats['pass_rate']}"

    def test_draft_exam_statistics():
        """1.5 草稿考试统计"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-A 草稿考试", exam_code=code, status="draft")
        
        stats = stats_service.get_exam_statistics(exam.id, hr_user)
        
        assert stats["total_participants"] == 0
        assert stats["completed_count"] == 0

    test("正常考试统计", test_normal_exam_statistics)
    test("无参与人员的考试统计", test_no_participants)
    test("有提交但无成绩的考试统计", test_no_score_records)
    test("多人考试成绩计算", test_multi_score_statistics)
    test("草稿考试统计", test_draft_exam_statistics)

    # ==================== 测试2: 权限控制测试 ====================
    print("\n[2] 权限控制测试")

    # 创建考试用于权限测试
    permission_code = get_unique_code()
    permission_exam = create_test_exam(db, hr_user, "S4.4-A 权限测试考试", exam_code=permission_code)

    def test_admin_can_view_all():
        """2.1 Admin 可以查看所有考试统计"""
        stats = stats_service.get_exam_statistics(permission_exam.id, admin_user)
        assert stats["exam_id"] == permission_exam.id

    def test_hr_can_view_own_exam():
        """2.2 HR 可以查看自己的考试统计"""
        stats = stats_service.get_exam_statistics(permission_exam.id, hr_user)
        assert stats["exam_id"] == permission_exam.id

    def test_hr_cannot_view_other_exam():
        """2.3 HR 不能查看其他 HR 的考试统计"""
        try:
            stats_service.get_exam_statistics(permission_exam.id, other_hr)
            raise Exception("应该抛出异常但未抛出")
        except ForbiddenException:
            pass

    def test_candidate_cannot_view():
        """2.4 候选人不能查看考试统计"""
        try:
            stats_service.get_exam_statistics(permission_exam.id, candidate_user)
            raise Exception("应该抛出异常但未抛出")
        except ForbiddenException:
            pass

    def test_nonexistent_exam():
        """2.5 查询不存在的考试"""
        try:
            stats_service.get_exam_statistics(99999, admin_user)
            raise Exception("应该抛出异常但未抛出")
        except NotFoundException:
            pass

    test("Admin 可以查看所有考试统计", test_admin_can_view_all)
    test("HR 可以查看自己的考试统计", test_hr_can_view_own_exam)
    test("HR 不能查看其他 HR 的考试统计", test_hr_cannot_view_other_exam)
    test("候选人不能查看考试统计", test_candidate_cannot_view)
    test("查询不存在的考试", test_nonexistent_exam)

    # ==================== 测试3: 候选人历史查询测试 ====================
    print("\n[3] 候选人历史查询测试")

    # 创建多场考试用于历史查询测试
    history_code1 = get_unique_code()
    history_exam1 = create_test_exam(db, hr_user, "S4.4-A 历史测试考试1", exam_code=history_code1)
    
    history_code2 = get_unique_code()
    history_exam2 = create_test_exam(db, hr_user, "S4.4-A 历史测试考试2", exam_code=history_code2)
    
    def test_candidate_history_found():
        """3.1 查询候选人历史考试（通过手机号）"""
        # 先清理该手机号的所有现有记录
        db.query(ExamRecord).filter(ExamRecord.candidate_phone == "13900000000").delete()
        db.commit()
        
        # 为候选人创建考试记录
        create_and_submit_exam_record(db, history_exam1.id, "张三", "13900000000", exam_code=history_code1, score=75)
        create_and_submit_exam_record(db, history_exam2.id, "张三", "13900000000", exam_code=history_code2, score=82)
        
        history = stats_service.get_candidate_history_by_phone("13900000000", admin_user)
        
        assert history["total_exams"] == 2, f"考试总数应为2，实际为{history['total_exams']}"
        assert history["completed_exams"] == 2, f"已完成数应为2，实际为{history['completed_exams']}"
        assert history["passed_exams"] == 2, f"通过数应为2，实际为{history['passed_exams']}"

    def test_candidate_history_empty():
        """3.2 查询空历史记录"""
        history = stats_service.get_candidate_history_by_phone("13999990000", admin_user)
        
        assert history["total_exams"] == 0
        assert history["history"] == []

    def test_candidate_history_permission():
        """3.3 权限测试：候选人不能查看他人历史"""
        try:
            stats_service.get_candidate_history_by_phone("13900000000", candidate_user)
            raise Exception("应该抛出异常但未抛出")
        except ForbiddenException:
            pass

    def test_candidate_self_history():
        """3.4 候选人可以查看自己的历史"""
        # 候选人用户的手机号是 13900000000
        history = stats_service.get_candidate_exam_history(candidate_user.id, candidate_user)
        assert history["candidate_id"] == candidate_user.id

    def test_cannot_view_other_candidate():
        """3.5 候选人不能查看其他候选人的历史"""
        try:
            stats_service.get_candidate_exam_history(admin_user.id, candidate_user)
            raise Exception("应该抛出异常但未抛出")
        except ForbiddenException:
            pass

    test("查询候选人历史考试成功", test_candidate_history_found)
    test("查询空历史记录", test_candidate_history_empty)
    test("候选人不能查看他人历史", test_candidate_history_permission)
    test("候选人可以查看自己的历史", test_candidate_self_history)
    test("候选人不能查看其他候选人的历史", test_cannot_view_other_candidate)

    # ==================== 测试4: 考试统计列表测试 ====================
    print("\n[4] 考试统计列表测试")

    def test_exam_statistics_list():
        """4.1 获取考试统计列表"""
        code1 = get_unique_code()
        exam1 = create_test_exam(db, hr_user, "S4.4-A 列表测试1", exam_code=code1)
        add_participant(db, exam1.id, "列表测试人员1", "13822220001")
        create_and_submit_exam_record(db, exam1.id, "列表测试人员1", "13822220001", exam_code=code1, score=70)
        
        code2 = get_unique_code()
        exam2 = create_test_exam(db, hr_user, "S4.4-A 列表测试2", exam_code=code2)
        add_participant(db, exam2.id, "列表测试人员2", "13822220002")
        create_and_submit_exam_record(db, exam2.id, "列表测试人员2", "13822220002", exam_code=code2, score=85)
        
        result = stats_service.get_exams_statistics_list(current_user=hr_user)
        
        assert result["total"] >= 2, f"考试总数至少为2，实际为{result['total']}"
        assert len(result["items"]) >= 2, f"列表项至少为2，实际为{len(result['items'])}"

    def test_exam_statistics_list_admin():
        """4.2 Admin 可以查看所有考试统计列表"""
        result = stats_service.get_exams_statistics_list(current_user=admin_user)
        assert result["total"] >= 0

    def test_exam_statistics_list_filter():
        """4.3 按状态筛选考试统计"""
        result = stats_service.get_exams_statistics_list(current_user=hr_user, status="published")
        for item in result["items"]:
            assert item.get("exam_status") == "published", f"状态筛选失败，实际状态为{item.get('exam_status')}"

    test("获取考试统计列表", test_exam_statistics_list)
    test("Admin 查看所有考试统计列表", test_exam_statistics_list_admin)
    test("按状态筛选考试统计", test_exam_statistics_list_filter)

    # ==================== 结果 ====================
    print("\n" + "=" * 70)
    total = passed + failed
    print(f"测试完成: {passed}/{total} 通过, {failed}/{total} 失败")
    if errors:
        print("\n失败详情:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print("=" * 70)

    db.close()
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
