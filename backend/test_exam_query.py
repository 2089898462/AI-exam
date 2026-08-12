"""
S4.4-B 数据查询接口建设测试
覆盖：
1. 考试分析查询接口测试
2. 考试成绩列表查询测试
3. 候选人历史查询增强测试（分页/排序/过滤）
4. 答题详情查询测试
5. 权限控制与数据隔离测试
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
from app.exceptions import ForbiddenException, NotFoundException

engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()


def cleanup_test_data(db):
    """清理所有 S4.4-B 测试数据"""
    exams = db.query(Exam).filter(Exam.title.like("%S4.4-B%")).all()
    exam_ids = [exam.id for exam in exams]

    if exam_ids:
        db.query(GradingRecord).filter(
            GradingRecord.exam_record_id.in_(
                db.query(ExamRecord.id).filter(ExamRecord.exam_id.in_(exam_ids))
            )
        ).delete(synchronize_session=False)

        db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id.in_(
                db.query(ExamRecord.id).filter(ExamRecord.exam_id.in_(exam_ids))
            )
        ).delete(synchronize_session=False)

        db.query(ExamRecord).filter(ExamRecord.exam_id.in_(exam_ids)).delete()
        db.query(ExamParticipant).filter(ExamParticipant.exam_id.in_(exam_ids)).delete()
        db.query(Question).filter(Question.exam_id.in_(exam_ids)).delete()
        db.query(Exam).filter(Exam.id.in_(exam_ids)).delete()

    users = db.query(User).filter(User.username.like("s4_4_b_%")).all()
    if users:
        user_phones = [u.phone for u in users if u.phone]
        if user_phones:
            db.query(ExamParticipant).filter(
                ExamParticipant.candidate_phone.in_(user_phones)
            ).delete(synchronize_session=False)

    if users:
        for user in users:
            db.delete(user)

    db.commit()


def get_or_create_user(db, username, role, display_name=None, phone=None):
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
    service = ExamService(db)
    exam = service.create_exam(
        title=title,
        duration_minutes=60,
        pass_score=pass_score,
        created_by=hr_user.id,
    )
    if exam_code:
        exam.exam_code = exam_code

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
    service = ExamParticipantService(db)
    return service.add_participant(
        exam_id=exam_id,
        candidate_name=name,
        candidate_phone=phone,
    )


def create_and_submit_exam_record(db, exam_id, candidate_name, candidate_phone, exam_code=None, score=None, skip_participant=False, create_answers=True):
    record_service = ExamRecordService(db)

    if not skip_participant:
        existing = db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam_id,
            ExamParticipant.candidate_phone == candidate_phone
        ).first()
        if not existing:
            add_participant(db, exam_id, candidate_name, candidate_phone)

    record = record_service.create_exam_record(
        exam_id=exam_id,
        candidate_name=candidate_name,
        candidate_phone=candidate_phone,
        exam_code=exam_code,
    )

    record_service.start_exam(record.id)

    # 如果需要创建答题记录
    if create_answers:
        questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        for q in questions:
            ar = AnswerRecord(
                exam_record_id=record.id,
                question_id=q.id,
                answer_content=q.answer,
                score=float(q.score) if score is not None else None,
                is_correct=True if score is not None else None,
            )
            db.add(ar)
        db.commit()

    record_service.submit_exam(record.id)

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
        record.score = score
        record.status = "graded"
        db.commit()

    db.refresh(record)
    return record


def run_tests():
    db = SessionLocal()
    cleanup_test_data(db)

    passed = 0
    failed = 0
    errors = []
    exam_counter = [0]

    def get_unique_code():
        exam_counter[0] += 1
        return f"S44B{exam_counter[0]:04d}"

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
    hr_user = get_or_create_user(db, "s4_4_b_hr", "hr", "S4.4-B HR")
    other_hr = get_or_create_user(db, "s4_4_b_other_hr", "hr", "S4.4-B Other HR")
    admin_user = get_or_create_user(db, "s4_4_b_admin", "admin", "S4.4-B Admin")
    candidate_user = get_or_create_user(db, "s4_4_b_candidate", "employee", "S4.4-B Candidate", phone="13900000000")
    other_candidate = get_or_create_user(db, "s4_4_b_candidate2", "employee", "S4.4-B Candidate2", phone="13900000001")

    stats_service = ExamStatisticsService(db)

    print("=" * 70)
    print("S4.4-B 数据查询接口建设测试")
    print("=" * 70)

    # ==================== 1. 考试分析查询测试 ====================
    print("\n[1] 考试分析查询接口测试")

    def test_exam_analysis_normal():
        """1.1 正常考试分析查询"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 分析测试", exam_code=code)
        add_participant(db, exam.id, "张三", "13800000101")
        create_and_submit_exam_record(db, exam.id, "张三", "13800000101", exam_code=code, score=85)

        analysis = stats_service.get_exam_analysis(exam.id, hr_user)

        assert analysis["exam_id"] == exam.id
        assert analysis["exam_title"] == "S4.4-B 分析测试"
        assert analysis["exam_status"] == "published"
        assert "created_at" in analysis
        assert "statistics" in analysis
        assert "answer_overview" in analysis
        stats = analysis["statistics"]
        assert stats["total_participants"] == 1
        assert stats["average_score"] == 85.0
        overview = analysis["answer_overview"]
        assert overview["total_questions"] == 1
        assert overview["total_score"] == 100.0

    def test_exam_analysis_admin_access():
        """1.2 Admin 可访问任意考试分析"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B Admin访问测试", exam_code=code)
        analysis = stats_service.get_exam_analysis(exam.id, admin_user)
        assert analysis["exam_id"] == exam.id

    def test_exam_analysis_forbidden():
        """1.3 候选人无权访问考试分析"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 禁止访问测试", exam_code=code)
        try:
            stats_service.get_exam_analysis(exam.id, candidate_user)
            assert False, "应该抛出 ForbiddenException"
        except ForbiddenException:
            pass

    def test_exam_analysis_other_hr_forbidden():
        """1.4 其他 HR 无权访问非自己管理的考试"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 越权HR测试", exam_code=code)
        try:
            stats_service.get_exam_analysis(exam.id, other_hr)
            assert False, "应该抛出 ForbiddenException"
        except ForbiddenException:
            pass

    def test_exam_analysis_not_found():
        """1.5 不存在的考试返回 404"""
        try:
            stats_service.get_exam_analysis(999999, hr_user)
            assert False, "应该抛出 NotFoundException"
        except NotFoundException:
            pass

    def test_exam_analysis_empty_exam():
        """1.6 空考试分析（无参与人员）"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 空考试分析", exam_code=code)
        analysis = stats_service.get_exam_analysis(exam.id, hr_user)
        assert analysis["statistics"]["total_participants"] == 0
        assert analysis["answer_overview"]["total_questions"] == 1
        assert analysis["answer_overview"]["answered_count"] == 0

    test("1.1 正常考试分析查询", test_exam_analysis_normal)
    test("1.2 Admin 可访问任意考试分析", test_exam_analysis_admin_access)
    test("1.3 候选人无权访问考试分析", test_exam_analysis_forbidden)
    test("1.4 其他 HR 无权访问非自己管理的考试", test_exam_analysis_other_hr_forbidden)
    test("1.5 不存在的考试返回 404", test_exam_analysis_not_found)
    test("1.6 空考试分析", test_exam_analysis_empty_exam)

    # ==================== 2. 考试成绩列表查询测试 ====================
    print("\n[2] 考试成绩列表查询测试")

    def test_exam_results_normal():
        """2.1 正常成绩列表查询"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 成绩列表测试", exam_code=code)
        create_and_submit_exam_record(db, exam.id, "张三", "13800000201", exam_code=code, score=80)
        create_and_submit_exam_record(db, exam.id, "李四", "13800000202", exam_code=code, score=50)

        results = stats_service.get_exam_results(exam.id, hr_user, page=1, page_size=20)
        assert results["exam_id"] == exam.id
        assert results["total"] == 2
        assert len(results["items"]) == 2
        for item in results["items"]:
            assert "record_id" in item
            assert "candidate_name" in item
            assert "score" in item
            assert "passed" in item

    def test_exam_results_pagination():
        """2.2 成绩列表分页"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 分页测试", exam_code=code)
        for i in range(5):
            phone = f"1380000030{i}"
            create_and_submit_exam_record(db, exam.id, f"考生{i}", phone, exam_code=code, score=50 + i * 10)

        page1 = stats_service.get_exam_results(exam.id, hr_user, page=1, page_size=2)
        assert len(page1["items"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1

        page2 = stats_service.get_exam_results(exam.id, hr_user, page=2, page_size=2)
        assert len(page2["items"]) == 2

        page3 = stats_service.get_exam_results(exam.id, hr_user, page=3, page_size=2)
        assert len(page3["items"]) == 1

    def test_exam_results_empty():
        """2.3 空考试成绩列表"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 空成绩列表", exam_code=code)
        results = stats_service.get_exam_results(exam.id, hr_user, page=1, page_size=20)
        assert results["total"] == 0
        assert len(results["items"]) == 0

    def test_exam_results_forbidden():
        """2.4 候选人无权查看成绩列表"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 禁止查看成绩", exam_code=code)
        try:
            stats_service.get_exam_results(exam.id, candidate_user)
            assert False
        except ForbiddenException:
            pass

    def test_exam_results_data_isolation():
        """2.5 HR 数据隔离"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 数据隔离测试", exam_code=code)
        create_and_submit_exam_record(db, exam.id, "张三", "13800000401", exam_code=code, score=75)
        try:
            stats_service.get_exam_results(exam.id, other_hr)
            assert False
        except ForbiddenException:
            pass

    test("2.1 正常成绩列表查询", test_exam_results_normal)
    test("2.2 成绩列表分页", test_exam_results_pagination)
    test("2.3 空考试成绩列表", test_exam_results_empty)
    test("2.4 候选人无权查看成绩列表", test_exam_results_forbidden)
    test("2.5 HR 数据隔离", test_exam_results_data_isolation)

    # ==================== 3. 候选人历史查询增强测试 ====================
    print("\n[3] 候选人历史查询增强测试")

    def test_candidate_history_paginated():
        """3.1 候选人历史分页查询"""
        code1 = get_unique_code()
        code2 = get_unique_code()
        # 为候选人创建两次考试记录
        exam1 = create_test_exam(db, hr_user, "S4.4-B 历史考试1", exam_code=code1)
        exam2 = create_test_exam(db, hr_user, "S4.4-B 历史考试2", exam_code=code2)
        create_and_submit_exam_record(db, exam1.id, "S4.4-B Candidate", "13900000000", exam_code=code1, score=90)
        create_and_submit_exam_record(db, exam2.id, "S4.4-B Candidate", "13900000000", exam_code=code2, score=75)

        result = stats_service.get_candidate_exam_history_paginated(
            candidate_user.id, admin_user, page=1, page_size=20
        )
        assert result["candidate_id"] == candidate_user.id
        assert result["total"] >= 2
        assert len(result["history"]) >= 2

    def test_candidate_history_sort():
        """3.2 候选人历史排序"""
        code1 = get_unique_code()
        code2 = get_unique_code()
        exam1 = create_test_exam(db, hr_user, "S4.4-B 排序考试1", exam_code=code1)
        exam2 = create_test_exam(db, hr_user, "S4.4-B 排序考试2", exam_code=code2)
        create_and_submit_exam_record(db, exam1.id, "S4.4-B Candidate", "13900000000", exam_code=code1, score=60)
        create_and_submit_exam_record(db, exam2.id, "S4.4-B Candidate", "13900000000", exam_code=code2, score=80)

        result = stats_service.get_candidate_exam_history_paginated(
            candidate_user.id, admin_user, page=1, page_size=20,
            sort_by="created_at", sort_order="desc"
        )
        assert result["history"][0]["exam_record_id"] >= result["history"][-1]["exam_record_id"]

    def test_candidate_history_status_filter():
        """3.3 候选人历史状态过滤"""
        code1 = get_unique_code()
        exam1 = create_test_exam(db, hr_user, "S4.4-B 过滤考试1", exam_code=code1)
        create_and_submit_exam_record(db, exam1.id, "S4.4-B Candidate", "13900000000", exam_code=code1, score=70)

        result = stats_service.get_candidate_exam_history_paginated(
            candidate_user.id, admin_user, page=1, page_size=20, status="graded"
        )
        for item in result["history"]:
            assert item["record_status"] == "graded"

    def test_candidate_history_self_access():
        """3.4 候选人可以查看自己的历史"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 自己历史测试", exam_code=code)
        create_and_submit_exam_record(db, exam.id, "S4.4-B Candidate", "13900000000", exam_code=code, score=85)

        result = stats_service.get_candidate_exam_history_paginated(
            candidate_user.id, candidate_user, page=1, page_size=20
        )
        assert result["candidate_id"] == candidate_user.id

    def test_candidate_history_cross_access_forbidden():
        """3.5 候选人不能查看他人历史"""
        try:
            stats_service.get_candidate_exam_history_paginated(
                other_candidate.id, candidate_user, page=1, page_size=20
            )
            assert False
        except ForbiddenException:
            pass

    def test_candidate_history_empty():
        """3.6 空历史记录"""
        # 使用新用户测试
        new_user = get_or_create_user(db, "s4_4_b_empty_candidate", "employee", "Empty Candidate", phone="13900009999")
        result = stats_service.get_candidate_exam_history_paginated(
            new_user.id, admin_user, page=1, page_size=20
        )
        assert result["total"] == 0
        assert len(result["history"]) == 0

    test("3.1 候选人历史分页查询", test_candidate_history_paginated)
    test("3.2 候选人历史排序", test_candidate_history_sort)
    test("3.3 候选人历史状态过滤", test_candidate_history_status_filter)
    test("3.4 候选人可以查看自己的历史", test_candidate_history_self_access)
    test("3.5 候选人不能查看他人历史", test_candidate_history_cross_access_forbidden)
    test("3.6 空历史记录", test_candidate_history_empty)

    # ==================== 4. 答题详情查询测试 ====================
    print("\n[4] 答题详情查询测试")

    def test_record_answers_normal():
        """4.1 正常答题详情查询"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 答题详情测试", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "张三", "13800000501", exam_code=code, score=100)

        answers = stats_service.get_record_answers(exam.id, record.id, hr_user)
        assert answers["exam_id"] == exam.id
        assert answers["record_id"] == record.id
        assert answers["candidate_name"] == "张三"
        assert answers["total_questions"] == 1
        assert "answers" in answers

    def test_record_answers_admin_access():
        """4.2 Admin 可访问任意答题详情"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B Admin答题测试", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "李四", "13800000502", exam_code=code, score=60)
        answers = stats_service.get_record_answers(exam.id, record.id, admin_user)
        assert answers["record_id"] == record.id

    def test_record_answers_self_access():
        """4.3 候选人可查看自己的答题详情"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 自己答题测试", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "S4.4-B Candidate", "13900000000", exam_code=code, score=70)

        answers = stats_service.get_record_answers(exam.id, record.id, candidate_user)
        assert answers["record_id"] == record.id

    def test_record_answers_cross_access_forbidden():
        """4.4 候选人不能查看他人答题详情"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 越权答题测试", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "其他人", "13800000600", exam_code=code, score=50)
        try:
            stats_service.get_record_answers(exam.id, record.id, candidate_user)
            assert False
        except ForbiddenException:
            pass

    def test_record_answers_other_hr_forbidden():
        """4.5 其他 HR 无权查看非自己管理的答题详情"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B HR越权答题", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "测试人", "13800000601", exam_code=code, score=55)
        try:
            stats_service.get_record_answers(exam.id, record.id, other_hr)
            assert False
        except ForbiddenException:
            pass

    def test_record_answers_not_found():
        """4.6 不存在的答题记录返回 404"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 不存在答题", exam_code=code)
        try:
            stats_service.get_record_answers(exam.id, 999999, hr_user)
            assert False
        except NotFoundException:
            pass

    def test_record_answers_empty():
        """4.7 无答案的答题详情"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 空答题详情", exam_code=code)
        record = create_and_submit_exam_record(db, exam.id, "空答案考生", "13800000701", exam_code=code, skip_participant=False, create_answers=False)
        answers = stats_service.get_record_answers(exam.id, record.id, hr_user)
        assert answers["total_questions"] == 0
        assert len(answers["answers"]) == 0

    test("4.1 正常答题详情查询", test_record_answers_normal)
    test("4.2 Admin 可访问任意答题详情", test_record_answers_admin_access)
    test("4.3 候选人可查看自己的答题详情", test_record_answers_self_access)
    test("4.4 候选人不能查看他人答题详情", test_record_answers_cross_access_forbidden)
    test("4.5 其他 HR 无权查看非自己管理的答题详情", test_record_answers_other_hr_forbidden)
    test("4.6 不存在的答题记录返回 404", test_record_answers_not_found)
    test("4.7 无答案的答题详情", test_record_answers_empty)

    # ==================== 5. 数据一致性测试 ====================
    print("\n[5] 数据一致性与完整性测试")

    def test_analysis_consistency_with_stats():
        """5.1 分析接口与统计接口数据一致性"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 一致性测试", exam_code=code)
        create_and_submit_exam_record(db, exam.id, "考生A", "13800000801", exam_code=code, score=88)
        create_and_submit_exam_record(db, exam.id, "考生B", "13800000802", exam_code=code, score=72)

        stats = stats_service.get_exam_statistics(exam.id, hr_user)
        analysis = stats_service.get_exam_analysis(exam.id, hr_user)

        assert analysis["statistics"]["total_participants"] == stats["total_participants"]
        assert analysis["statistics"]["completed_count"] == stats["completed_count"]
        assert analysis["statistics"]["average_score"] == stats["average_score"]
        assert analysis["statistics"]["pass_count"] == stats["pass_count"]

    def test_results_consistency_with_analysis():
        """5.2 成绩列表与分析接口数据一致性"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, "S4.4-B 成绩一致性测试", exam_code=code)
        create_and_submit_exam_record(db, exam.id, "考生X", "13800000901", exam_code=code, score=55)

        results = stats_service.get_exam_results(exam.id, hr_user, page=1, page_size=20)
        analysis = stats_service.get_exam_analysis(exam.id, hr_user)

        assert results["total"] == analysis["statistics"]["completed_count"]
        assert len(results["items"]) == analysis["statistics"]["completed_count"]

    def test_multiple_exams_isolation():
        """5.3 多考试数据隔离"""
        code1 = get_unique_code()
        code2 = get_unique_code()
        exam1 = create_test_exam(db, hr_user, "S4.4-B 隔离考试1", exam_code=code1)
        exam2 = create_test_exam(db, hr_user, "S4.4-B 隔离考试2", exam_code=code2)
        create_and_submit_exam_record(db, exam1.id, "考生1", "13800001001", exam_code=code1, score=90)
        create_and_submit_exam_record(db, exam2.id, "考生2", "13800001002", exam_code=code2, score=60)

        analysis1 = stats_service.get_exam_analysis(exam1.id, hr_user)
        analysis2 = stats_service.get_exam_analysis(exam2.id, hr_user)

        assert analysis1["exam_id"] != analysis2["exam_id"]
        assert analysis1["statistics"]["total_participants"] == 1
        assert analysis2["statistics"]["total_participants"] == 1

    test("5.1 分析接口与统计接口数据一致性", test_analysis_consistency_with_stats)
    test("5.2 成绩列表与分析接口数据一致性", test_results_consistency_with_analysis)
    test("5.3 多考试数据隔离", test_multiple_exams_isolation)

    # ==================== 结果汇总 ====================
    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if errors:
        print("\n失败详情:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    db.close()
    return passed, failed, errors


if __name__ == "__main__":
    passed, failed, errors = run_tests()
    sys.exit(0 if failed == 0 else 1)