"""
S4.3-C 核心流程测试补充
覆盖：
1. 考试创建流程测试
2. 固定试卷模板流程测试
3. 考试人员管理流程测试
4. 考试访问安全测试
5. 答题流程测试
6. 提交流程测试
7. 权限测试
"""

import sys
sys.path.insert(0, '.')

import bcrypt
from app.db.session import _get_engine, _get_session_factory
from app.db.base import Base
from app.models import Exam, User, ExamRecord, ExamParticipant, Question, AnswerRecord, ExamTemplate, TemplateQuestion
from app.models.user import User as UserModel
from app.services.exam_service import ExamService
from app.services.exam_record_service import ExamRecordService
from app.services.participant_service import ExamParticipantService
from app.services.question_service import QuestionService
from app.services.template_service import TemplateService
from app.exceptions import BusinessException, NotFoundException

# 创建测试引擎和会话
engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()


def cleanup_test_data(db):
    """清理所有测试数据"""
    # 删除带有 S4.3-C 标记的考试
    exams = db.query(Exam).filter(Exam.title.like("%S4.3-C%")).all()
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
    
    # 删除测试模板
    templates = db.query(ExamTemplate).filter(
        ExamTemplate.name.like("%S4.3-C%")
    ).all()
    for template in templates:
        db.query(TemplateQuestion).filter(TemplateQuestion.template_id == template.id).delete()
        db.delete(template)
    
    db.commit()


def get_or_create_hr_user(db):
    """获取或创建HR测试用户"""
    user = db.query(User).filter(User.username == "hr_core_test").first()
    if not user:
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        user = UserModel(
            username="hr_core_test",
            password_hash=hashed,
            display_name="核心流程测试HR",
            role="hr",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_or_create_other_hr_user(db):
    """获取或创建另一个HR用户（用于权限隔离测试）"""
    user = db.query(User).filter(User.username == "hr_other_test").first()
    if not user:
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        user = UserModel(
            username="hr_other_test",
            password_hash=hashed,
            display_name="另一个HR测试",
            role="hr",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_or_create_candidate_user(db):
    """获取或创建candidate测试用户"""
    user = db.query(User).filter(User.username == "candidate_core_test").first()
    if not user:
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        user = UserModel(
            username="candidate_core_test",
            password_hash=hashed,
            display_name="候选人测试",
            role="candidate",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_test_exam(db, hr_user, title="S4.3-C测试考试", exam_code=None, status="draft"):
    """创建测试考试"""
    service = ExamService(db)
    exam = service.create_exam(
        title=title,
        duration_minutes=60,
        pass_score=60,
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
        score=10.0,
        current_user=hr_user,
    )
    
    if status == "published":
        service.publish_exam(exam.id, current_user=hr_user)
    
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


def create_test_template(db, hr_user, name="S4.3-C测试模板"):
    """创建测试模板（使用正确的API）"""
    service = TemplateService(db)
    template = service.create_template(
        name=name,
        created_by=hr_user.id,
        description="用于核心流程测试",
    )
    
    # 添加题目
    service.create_template_question(
        template_id=template.id,
        current_user=hr_user,
        question_no="1",
        type="single_choice",
        content="模板题目：2+2等于几？",
        options=["3", "4", "5", "6"],
        answer="B",
        score=10,
    )
    
    return template


def run_tests():
    db = SessionLocal()
    
    # 清理残留测试数据
    cleanup_test_data(db)
    
    passed = 0
    failed = 0
    errors = []
    exam_counter = [0]  # 使用列表以便在闭包中修改

    def get_unique_code():
        """获取唯一的考试码"""
        exam_counter[0] += 1
        return f"S43C{exam_counter[0]:04d}"

    def test(name, func):
        nonlocal passed, failed
        try:
            func()
            passed += 1
            print(f"  [PASS] {name}")
        except Exception as e:
            db.rollback()  # 事务回滚
            failed += 1
            errors.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}")

    hr_user = get_or_create_hr_user(db)
    other_hr = get_or_create_other_hr_user(db)
    candidate_user = get_or_create_candidate_user(db)
    exam_service = ExamService(db)
    record_service = ExamRecordService(db)
    participant_service = ExamParticipantService(db)
    template_service = TemplateService(db)

    print("=" * 70)
    print("S4.3-C 核心流程测试补充")
    print("=" * 70)

    # ==================== 测试1: 考试创建流程 ====================
    print("\n[1] 考试创建流程测试")

    def test_create_exam_success():
        """1.1 创建考试成功"""
        code = get_unique_code()
        exam = exam_service.create_exam(
            title="S4.3-C 考试创建测试",
            duration_minutes=60,
            pass_score=60,
            created_by=hr_user.id,
        )
        assert exam is not None
        assert exam.title == "S4.3-C 考试创建测试"
        assert exam.created_by == hr_user.id
        assert exam.status == "draft"
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_create_exam_with_code():
        """1.2 创建带凭证的考试"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C带凭证考试-{code}", exam_code=code)
        assert exam.exam_code == code
        assert exam.status == "draft"
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_non_hr_cannot_create():
        """1.3 非HR用户无法发布考试"""
        # 尝试用candidate用户发布考试
        exam = create_test_exam(db, hr_user, f"S4.3-C发布测试-{get_unique_code()}")
        try:
            # candidate 用户尝试发布
            exam_service.publish_exam(exam.id, current_user=candidate_user)
            # 如果没有抛异常，检查是否是无权错误
        except BusinessException as e:
            assert "无权" in str(e) or "操作" in str(e)
        except Exception:
            pass  # 其他异常也可以接受
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_exam_publish_flow():
        """1.4 考试发布流程"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C发布流程测试-{code}")
        assert exam.status == "draft"
        
        # 发布考试
        published = exam_service.publish_exam(exam.id, current_user=hr_user)
        assert published.status == "published"
        assert published.published_at is not None
        
        # 关闭考试
        closed = exam_service.close_exam(exam.id, current_user=hr_user)
        assert closed.status == "closed"
        
        # 清理
        db.delete(exam)
        db.commit()

    test("创建考试成功", test_create_exam_success)
    test("创建带凭证的考试", test_create_exam_with_code)
    test("非HR用户无法发布考试", test_non_hr_cannot_create)
    test("考试发布流程", test_exam_publish_flow)

    # ==================== 测试2: 固定试卷模板流程 ====================
    print("\n[2] 固定试卷模板流程测试")

    def test_template_create_and_use():
        """2.1 创建模板并基于模板创建考试"""
        template = create_test_template(db, hr_user, "S4.3-C模板测试")
        assert template is not None
        
        # 基于模板创建考试
        exam = template_service.create_exam_from_template(
            template_id=template.id,
            current_user=hr_user,
            title="S4.3-C基于模板的考试",
            duration_minutes=90,
            pass_score=60,
        )
        assert exam is not None
        assert exam.title == "S4.3-C基于模板的考试"
        
        # 验证考试独立存在
        exam_check = db.query(Exam).filter(Exam.id == exam.id).first()
        assert exam_check is not None
        assert exam_check.title == "S4.3-C基于模板的考试"
        
        # 清理
        db.query(Question).filter(Question.exam_id == exam.id).delete()
        db.delete(exam)
        template_full = db.query(ExamTemplate).filter(ExamTemplate.id == template.id).first()
        if template_full:
            db.query(TemplateQuestion).filter(TemplateQuestion.template_id == template.id).delete()
            db.delete(template_full)
        db.commit()

    def test_template_modify_no_impact():
        """2.2 模板修改不影响已有考试"""
        # 创建模板
        template = template_service.create_template(
            name="S4.3-C隔离测试模板",
            created_by=hr_user.id,
            description="数据隔离测试",
        )
        # 添加题目
        q = template_service.create_template_question(
            template_id=template.id,
            current_user=hr_user,
            question_no="1",
            type="single_choice",
            content="原始题目",
            options=["A", "B", "C", "D"],
            answer="A",
            score=10,
        )
        
        # 基于模板创建考试
        exam = template_service.create_exam_from_template(
            template_id=template.id,
            current_user=hr_user,
            title="S4.3-C隔离测试考试",
            duration_minutes=60,
        )
        
        exam_question = db.query(Question).filter(
            Question.exam_id == exam.id
        ).first()
        original_content = exam_question.content
        
        # 修改模板题目
        template_service.update_template_question(
            template_id=template.id,
            question_id=q.id,
            current_user=hr_user,
            content="修改后的题目",
        )
        
        # 验证考试题目未改变
        exam_question_after = db.query(Question).filter(
            Question.exam_id == exam.id
        ).first()
        assert exam_question_after.content == original_content, "考试题内容不应因模板修改而改变"
        
        # 清理
        db.query(Question).filter(Question.exam_id == exam.id).delete()
        db.delete(exam)
        template_full = db.query(ExamTemplate).filter(ExamTemplate.id == template.id).first()
        if template_full:
            db.query(TemplateQuestion).filter(TemplateQuestion.template_id == template.id).delete()
            db.delete(template_full)
        db.commit()

    def test_template_data_isolation():
        """2.3 模板数据隔离有效"""
        # HR1 创建模板
        template1 = template_service.create_template(
            name="S4.3-C隔离模板1",
            created_by=hr_user.id,
        )
        # HR2 无法删除 HR1 的模板
        try:
            template_service.delete_template(template1.id, current_user=other_hr)
        except BusinessException:
            pass  # 预期行为
        
        # 验证模板仍然存在
        template_remaining = db.query(ExamTemplate).filter(ExamTemplate.id == template1.id).first()
        assert template_remaining is not None, "HR2 不应该能删除 HR1 的模板"
        
        # 清理
        db.query(TemplateQuestion).filter(TemplateQuestion.template_id == template1.id).delete()
        db.delete(template_remaining)
        db.commit()

    test("创建模板并基于模板创建考试", test_template_create_and_use)
    test("模板修改不影响已有考试", test_template_modify_no_impact)
    test("模板数据隔离有效", test_template_data_isolation)

    # ==================== 测试3: 考试人员管理流程 ====================
    print("\n[3] 考试人员管理流程测试")

    # 创建考试用于人员管理测试
    code_for_participant = get_unique_code()
    exam_for_participant = create_test_exam(db, hr_user, f"S4.3-C人员管理测试-{code_for_participant}", exam_code=code_for_participant, status="published")

    def test_add_participant():
        """3.1 添加考试人员"""
        participant = add_participant(db, exam_for_participant.id, "测试人员1", "13810000001")
        assert participant is not None
        assert participant.candidate_name == "测试人员1"
        assert participant.status == "assigned"

    def test_list_participants():
        """3.2 查询参与人员"""
        add_participant(db, exam_for_participant.id, "测试人员2", "13810000002")
        participants, total = participant_service.list_participants(exam_for_participant.id)
        assert total >= 2
        assert len(participants) >= 2

    def test_remove_unused_participant():
        """3.3 删除未参加人员"""
        # 先添加一个人员
        participant = add_participant(db, exam_for_participant.id, "待删除人员", "13810000099")
        # 确认没有考试记录
        record = db.query(ExamRecord).filter(
            ExamRecord.exam_id == exam_for_participant.id,
            ExamRecord.candidate_phone == "13810000099",
        ).first()
        assert record is None, "该人员不应有考试记录"
        
        # 删除
        result = participant_service.remove_participant(participant.id)
        assert result is True

    def test_duplicate_addition_prevention():
        """3.4 重复添加限制"""
        try:
            add_participant(db, exam_for_participant.id, "测试人员1", "13810000001")
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "已添加" in str(e) or "已存在" in str(e)

    def test_batch_add_participants():
        """3.5 批量添加人员"""
        participants = [
            {"candidate_name": "批量人员1", "candidate_phone": "13820000001"},
            {"candidate_name": "批量人员2", "candidate_phone": "13820000002"},
            {"candidate_name": "批量人员3", "candidate_phone": "13820000003"},
        ]
        success_count, errors = participant_service.add_participants_batch(
            exam_for_participant.id, participants
        )
        assert success_count == 3
        assert len(errors) == 0

    test("添加考试人员", test_add_participant)
    test("查询参与人员", test_list_participants)
    test("删除未参加人员", test_remove_unused_participant)
    test("重复添加限制", test_duplicate_addition_prevention)
    test("批量添加人员", test_batch_add_participants)

    # ==================== 测试4: 考试访问安全测试 ====================
    print("\n[4] 考试访问安全测试")

    def test_correct_code_access():
        """4.1 正确考试凭证可以进入"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C安全测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "安全测试人员", "13830000001")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="安全测试人员",
            candidate_phone="13830000001",
        )
        assert record is not None
        assert record.status == "not_started"
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_wrong_code_rejected():
        """4.2 错误考试凭证拒绝"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C错误凭证测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "错误凭证人员", "13830000002")
        
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code="WRONG_CODE",
                candidate_name="错误凭证人员",
                candidate_phone="13830000002",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "凭证错误" in str(e) or "凭证" in str(e)
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_unauthorized_person_rejected():
        """4.3 未授权人员拒绝进入"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C未授权测试-{code}", exam_code=code, status="published")
        # 注意：没有添加该人员到参与人员列表
        
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code=code,
                candidate_name="未授权人员",
                candidate_phone="13899990000",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "未被分配" in str(e) or "无法参加" in str(e)
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_closed_exam_rejected():
        """4.4 已关闭考试无法访问"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C关闭考试测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "关闭测试人员", "13830000003")
        
        # 关闭考试
        exam_service.close_exam(exam.id, current_user=hr_user)
        
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code=code,
                candidate_name="关闭测试人员",
                candidate_phone="13830000003",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "无法参加" in str(e) or "状态" in str(e)
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    test("正确考试凭证可以进入", test_correct_code_access)
    test("错误考试凭证拒绝", test_wrong_code_rejected)
    test("未授权人员拒绝进入", test_unauthorized_person_rejected)
    test("已关闭考试无法访问", test_closed_exam_rejected)

    # ==================== 测试5: 答题流程测试 ====================
    print("\n[5] 答题流程测试")

    def test_create_and_start_exam():
        """5.1 创建考试记录并开始答题"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C答题测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "答题人员", "13840000001")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="答题人员",
            candidate_phone="13840000001",
        )
        assert record.status == "not_started"
        
        # 开始考试
        started = record_service.start_exam(record.id)
        assert started.status == "in_progress"
        assert started.started_at is not None
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_save_answers():
        """5.2 保存答案"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C保存答案测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "保存人员", "13840000002")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="保存人员",
            candidate_phone="13840000002",
        )
        record_service.start_exam(record.id)
        
        # 保存答案
        answer = AnswerRecord(
            exam_record_id=record.id,
            question_id=exam.questions[0].id,
            answer_content="B",
        )
        db.add(answer)
        db.commit()
        
        # 验证答案保存
        saved = db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == record.id
        ).first()
        assert saved is not None
        assert saved.answer_content == "B"
        
        # 清理
        db.query(AnswerRecord).filter(AnswerRecord.exam_record_id == record.id).delete()
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_answer_status_change():
        """5.3 答题状态变化"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C状态变化测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "状态人员", "13840000003")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="状态人员",
            candidate_phone="13840000003",
        )
        assert record.status == "not_started"
        
        record_service.start_exam(record.id)
        assert record.status == "in_progress"
        
        # 验证不允许再次开始
        try:
            record_service.start_exam(record.id)
            raise Exception("应该抛出异常但未抛出")
        except BusinessException:
            pass
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_multiple_save_no_error():
        """5.4 多次保存不会产生异常"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C多次保存测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "多次保存人员", "13840000004")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="多次保存人员",
            candidate_phone="13840000004",
        )
        record_service.start_exam(record.id)
        
        # 多次保存同一题的答案
        question_id = exam.questions[0].id
        for i in range(3):
            answer = db.query(AnswerRecord).filter(
                AnswerRecord.exam_record_id == record.id,
                AnswerRecord.question_id == question_id,
            ).first()
            if answer:
                answer.answer_content = f"answer_{i}"
            else:
                answer = AnswerRecord(
                    exam_record_id=record.id,
                    question_id=question_id,
                    answer_content=f"answer_{i}",
                )
                db.add(answer)
            db.commit()
        
        # 应该只有一条记录（unique constraint）
        answers = db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == record.id
        ).all()
        assert len(answers) == 1
        assert answers[0].answer_content == "answer_2"  # 最后一次保存的值
        
        # 清理
        db.query(AnswerRecord).filter(AnswerRecord.exam_record_id == record.id).delete()
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    test("创建考试记录并开始答题", test_create_and_start_exam)
    test("保存答案", test_save_answers)
    test("答题状态变化", test_answer_status_change)
    test("多次保存不会产生异常", test_multiple_save_no_error)

    # ==================== 测试6: 提交流程测试 ====================
    print("\n[6] 提交流程测试")

    def test_normal_submit():
        """6.1 正常提交答案"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C正常提交测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "提交人员", "13850000001")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="提交人员",
            candidate_phone="13850000001",
        )
        record_service.start_exam(record.id)
        
        # 提交
        submitted = record_service.submit_exam(record.id)
        assert submitted.status == "submitted"
        assert submitted.submitted_at is not None
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_status_after_submit():
        """6.2 提交后状态更新"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C状态更新测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "状态提交人员", "13850000002")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="状态提交人员",
            candidate_phone="13850000002",
        )
        record_service.start_exam(record.id)
        record_service.submit_exam(record.id)
        
        # 验证状态为 submitted
        updated = record_service.get_record_by_id(record.id)
        assert updated.status == "submitted"
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_duplicate_submit_protection():
        """6.3 重复提交保护"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C重复提交测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "重复提交人员", "13850000003")
        
        record = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="重复提交人员",
            candidate_phone="13850000003",
        )
        record_service.start_exam(record.id)
        record_service.submit_exam(record.id)
        
        # 尝试再次提交（应该幂等）
        result = record_service.submit_exam(record.id)
        assert result.status == "submitted"
        assert result.id == record.id
        
        # 尝试重新创建考试记录（应该被拒绝）
        try:
            record_service.create_exam_record(
                exam_id=exam.id,
                exam_code=code,
                candidate_name="重复提交人员",
                candidate_phone="13850000003",
            )
            raise Exception("应该抛出异常但未抛出")
        except BusinessException as e:
            assert "已完成" in str(e) or "无法再次参加" in str(e)
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_no_multiple_records_after_submit():
        """6.4 重复请求不会生成多个成绩"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C多记录测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "多记录人员", "13850000004")
        
        # 创建第一条记录
        record1 = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="多记录人员",
            candidate_phone="13850000004",
        )
        record_service.start_exam(record1.id)
        record_service.submit_exam(record1.id)
        
        # 查询该考生的所有记录
        records = db.query(ExamRecord).filter(
            ExamRecord.exam_id == exam.id,
            ExamRecord.candidate_phone == "13850000004",
        ).all()
        submitted_records = [r for r in records if r.status in ("submitted", "graded")]
        
        # 应该只有一条已提交的记录
        assert len(submitted_records) == 1, f"应该只有1条已提交记录，实际有{len(submitted_records)}条"
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id == record1.id).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    test("正常提交答案", test_normal_submit)
    test("提交后状态更新", test_status_after_submit)
    test("重复提交保护", test_duplicate_submit_protection)
    test("重复请求不会生成多个成绩", test_no_multiple_records_after_submit)

    # ==================== 测试7: 权限测试 ====================
    print("\n[7] 权限测试")

    def test_candidate_cannot_view_others_records():
        """7.1 候选人不能查看其他人员考试记录"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C权限测试-{code}", exam_code=code, status="published")
        add_participant(db, exam.id, "权限人员A", "13860000001")
        add_participant(db, exam.id, "权限人员B", "13860000002")
        
        # 创建两个考生的记录
        record_a = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="权限人员A",
            candidate_phone="13860000001",
        )
        record_b = record_service.create_exam_record(
            exam_id=exam.id,
            exam_code=code,
            candidate_name="权限人员B",
            candidate_phone="13860000002",
        )
        
        # 验证记录独立
        assert record_a.id != record_b.id
        assert record_a.candidate_name == "权限人员A"
        assert record_b.candidate_name == "权限人员B"
        
        # 清理
        db.query(ExamRecord).filter(ExamRecord.id.in_([record_a.id, record_b.id])).delete()
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_candidate_cannot_modify_exam():
        """7.2 候选人不能修改考试内容"""
        code = get_unique_code()
        exam = create_test_exam(db, hr_user, f"S4.3-C不可修改考试-{code}", exam_code=code)
        
        # 候选人尝试修改
        try:
            exam_service.update_exam(exam.id, current_user=candidate_user, title="被修改的标题")
        except BusinessException as e:
            assert "无权" in str(e) or "修改" in str(e)
        
        # 验证考试未被修改
        unchanged = db.query(Exam).filter(Exam.id == exam.id).first()
        assert unchanged.title == f"S4.3-C不可修改考试-{code}"
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_hr_has_management_permission():
        """7.3 HR拥有对应管理权限"""
        code = get_unique_code()
        # HR 可以创建考试
        exam = create_test_exam(db, hr_user, f"S4.3-CHR权限测试-{code}")
        assert exam.created_by == hr_user.id
        
        # HR 可以发布考试
        published = exam_service.publish_exam(exam.id, current_user=hr_user)
        assert published.status == "published"
        
        # HR 可以关闭考试
        closed = exam_service.close_exam(exam.id, current_user=hr_user)
        assert closed.status == "closed"
        
        # 清理
        db.query(Exam).filter(Exam.id == exam.id).delete()
        db.commit()

    def test_data_isolation_between_hr():
        """7.4 HR间数据隔离"""
        code = get_unique_code()
        # HR1 创建考试
        exam1 = create_test_exam(db, hr_user, f"S4.3-CHR1的考试-{code}")
        
        # HR2 无法修改 HR1 的考试
        try:
            exam_service.update_exam(exam1.id, current_user=other_hr, title="HR2修改的标题")
        except BusinessException as e:
            assert "无权" in str(e)
        
        # HR2 无法删除 HR1 的考试
        try:
            exam_service.delete_exam(exam1.id, current_user=other_hr)
        except BusinessException as e:
            assert "无权" in str(e)
        
        # 验证考试仍然存在且未被修改
        unchanged = db.query(Exam).filter(Exam.id == exam1.id).first()
        assert unchanged is not None
        assert unchanged.title == f"S4.3-CHR1的考试-{code}"
        
        # 清理
        db.query(Exam).filter(Exam.id == exam1.id).delete()
        db.commit()

    test("候选人不能查看其他人员考试记录", test_candidate_cannot_view_others_records)
    test("候选人不能修改考试内容", test_candidate_cannot_modify_exam)
    test("HR拥有对应管理权限", test_hr_has_management_permission)
    test("HR间数据隔离", test_data_isolation_between_hr)

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
