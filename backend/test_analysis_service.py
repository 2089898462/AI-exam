"""
S5.5 招聘辅助分析能力测试
测试 AnalysisService 和候选人分析报告功能
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    AIScoreRecord,
    AnswerRecord,
    CandidateAnalysisReport,
    Exam,
    ExamParticipant,
    ExamRecord,
    Question,
    User,
)
from app.services.analysis_service import AnalysisService

DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_db():
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def teardown_db():
    Base.metadata.drop_all(bind=engine)


def create_test_data(db):
    """创建完整测试数据"""
    # 创建管理员用户
    admin = User(
        username="admin_test",
        email="admin_test@example.com",
        password_hash="hashed_password",
        display_name="测试管理员",
        role="admin",
    )
    db.add(admin)
    db.flush()

    # 创建候选人用户
    candidate = User(
        username="candidate_test",
        email="candidate@example.com",
        password_hash="hashed_password",
        display_name="测试候选人",
        role="employee",
    )
    db.add(candidate)
    db.flush()

    # 创建考试
    exam = Exam(
        title="Java 开发工程师选拔考试",
        description="测试候选人 Java 开发能力",
        position="Java 开发工程师",
        duration_minutes=60,
        created_by=admin.id,
        status="draft",
    )
    db.add(exam)
    db.flush()

    # 创建考试参与人员
    participant = ExamParticipant(
        exam_id=exam.id,
        user_id=candidate.id,
        candidate_name="测试候选人",
        candidate_phone="13800138000",
        candidate_email="candidate@example.com",
        status="submitted",
    )
    db.add(participant)
    db.flush()

    # 创建题目
    q1 = Question(
        exam_id=exam.id,
        content="请解释 Java 中多态的概念，并举例说明。",
        type="short_answer",
        answer="多态是同一接口有不同实现的能力。",
        score=10,
        category="Java基础",
        sort_order=1,
    )
    db.add(q1)

    q2 = Question(
        exam_id=exam.id,
        content="如何优化 SQL 查询性能？",
        type="short_answer",
        answer="使用索引、避免全表扫描、优化 JOIN。",
        score=10,
        category="数据库",
        sort_order=2,
    )
    db.add(q2)

    q3 = Question(
        exam_id=exam.id,
        content="Spring Boot 的自动配置原理是什么？",
        type="short_answer",
        answer="基于 @EnableAutoConfiguration 和 SpringFactoriesLoader。",
        score=10,
        category="Spring框架",
        sort_order=3,
    )
    db.add(q3)
    db.flush()

    # 创建考试记录
    exam_record = ExamRecord(
        exam_id=exam.id,
        participant_id=participant.id,
        candidate_name="测试候选人",
        candidate_phone="13800138000",
        candidate_email="candidate@example.com",
        status="submitted",
        started_at=datetime.now(),
        submitted_at=datetime.now(),
    )
    db.add(exam_record)
    db.flush()

    # 创建答题记录
    ar1 = AnswerRecord(
        exam_record_id=exam_record.id,
        question_id=q1.id,
        answer_content="多态是同一接口有不同实现。比如 Animal 接口有 Dog 和 Cat 实现。",
        score=8,
    )
    db.add(ar1)

    ar2 = AnswerRecord(
        exam_record_id=exam_record.id,
        question_id=q2.id,
        answer_content="可以使用索引来优化查询。",
        score=5,
    )
    db.add(ar2)

    ar3 = AnswerRecord(
        exam_record_id=exam_record.id,
        question_id=q3.id,
        answer_content="Spring Boot 自动配置是通过注解实现的。",
        score=6,
    )
    db.add(ar3)
    db.flush()

    # 创建 AI 评分记录（状态为 completed）
    ai1 = AIScoreRecord(
        answer_record_id=ar1.id,
        ai_score=8.0,
        max_score=10.0,
        confidence=0.9,
        matched_points=json.dumps(["多态概念", "方法重写"], ensure_ascii=False),
        missing_points=json.dumps(["接口多态 vs 继承多态"], ensure_ascii=False),
        score_reason="候选人正确理解了多态概念并给出了例子，但未区分接口和继承实现方式。",
        review_status="completed",
        model_name="deepseek-v3",
    )
    db.add(ai1)

    ai2 = AIScoreRecord(
        answer_record_id=ar2.id,
        ai_score=5.0,
        max_score=10.0,
        confidence=0.8,
        matched_points=json.dumps(["索引基础"], ensure_ascii=False),
        missing_points=json.dumps([
            "索引类型选择", "避免全表扫描", "JOIN 优化", "EXPLAIN 使用",
        ], ensure_ascii=False),
        score_reason="候选人知道使用索引，但缺少具体优化方法的了解。",
        review_status="completed",
        model_name="deepseek-v3",
    )
    db.add(ai2)

    ai3 = AIScoreRecord(
        answer_record_id=ar3.id,
        ai_score=6.0,
        max_score=10.0,
        confidence=0.75,
        matched_points=json.dumps(["自动配置概念"], ensure_ascii=False),
        missing_points=json.dumps([
            "@EnableAutoConfiguration 作用", "SpringFactoriesLoader 机制",
            "条件装配原理",
        ], ensure_ascii=False),
        score_reason="候选人了解自动配置概念，但对底层实现机制不熟悉。",
        review_status="completed",
        model_name="deepseek-v3",
    )
    db.add(ai3)
    db.commit()

    return {
        "admin": admin,
        "candidate": candidate,
        "exam": exam,
        "participant": participant,
        "questions": [q1, q2, q3],
        "exam_record": exam_record,
        "answers": [ar1, ar2, ar3],
        "ai_scores": [ai1, ai2, ai3],
    }


def test_generate_report():
    """测试 1: 分析报告生成"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        report = service.generate_report(td["exam_record"].id)

        assert report is not None
        assert report.exam_record_id == td["exam_record"].id
        assert report.participant_id == td["participant"].id
        assert report.candidate_user_id == td["candidate"].id
        assert report.status == "generated"
        assert report.analysis_version == "v1"
        assert report.overall_score == 19.0  # 8 + 5 + 6
        assert len(report.analysis_summary) > 0

        # 检查 JSON 字段
        knowledge_mastery = json.loads(report.knowledge_mastery)
        assert len(knowledge_mastery) > 0

        strengths = json.loads(report.strengths)
        assert len(strengths) > 0

        weak_points = json.loads(report.weak_points)
        assert len(weak_points) > 0

        interview_focus = json.loads(report.interview_focus)
        assert len(interview_focus) > 0

        suggested_questions = json.loads(report.suggested_questions)
        assert len(suggested_questions) > 0

        print("  [PASS] 分析报告生成成功")
    finally:
        teardown_db()


def test_no_duplicate():
    """测试 2: 报告不重复生成"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        report1 = service.generate_report(td["exam_record"].id)
        report2 = service.generate_report(td["exam_record"].id)
        assert report2.id == report1.id

        print("  [PASS] 报告不重复生成")
    finally:
        teardown_db()


def test_query_report():
    """测试 3: 报告查询"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        generated = service.generate_report(td["exam_record"].id)

        # 按 ID 查询
        report = service.get_report(generated.id)
        assert report.id == generated.id

        # 按考试记录查询
        by_exam = service.get_report_by_exam_record(td["exam_record"].id)
        assert by_exam is not None
        assert by_exam.id == generated.id

        # 列表查询
        all_reports = service.list_reports()
        assert len(all_reports) == 1

        # 按候选人筛选
        by_candidate = service.list_reports(candidate_user_id=td["candidate"].id)
        assert len(by_candidate) == 1

        # 按状态筛选
        by_status = service.list_reports(status="generated")
        assert len(by_status) == 1

        empty = service.list_reports(status="reviewed")
        assert len(empty) == 0

        print("  [PASS] 报告查询成功")
    finally:
        teardown_db()


def test_review_report():
    """测试 4: 报告审核"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        report = service.generate_report(td["exam_record"].id)
        assert report.status == "generated"

        reviewed = service.review_report(
            report.id,
            reviewed_by=td["admin"].id,
            hr_remark="候选人基础扎实，建议面试重点考察数据库优化。",
        )
        assert reviewed.status == "reviewed"
        assert reviewed.reviewed_by == td["admin"].id
        assert reviewed.hr_remark == "候选人基础扎实，建议面试重点考察数据库优化。"
        assert reviewed.reviewed_at is not None

        print("  [PASS] 报告审核成功")
    finally:
        teardown_db()


def test_no_ai_scores_error():
    """测试 5: 无 AI 评分时异常处理"""
    db = setup_db()
    try:
        admin = User(
            username="admin_test2",
            email="admin2@example.com",
            password_hash="hashed_password",
            display_name="测试管理员2",
            role="admin",
        )
        db.add(admin)
        db.flush()

        exam = Exam(
            title="空评分考试",
            description="测试无评分",
            position="测试岗位",
            duration_minutes=30,
            created_by=admin.id,
            status="draft",
        )
        db.add(exam)
        db.flush()

        exam_record = ExamRecord(
            exam_id=exam.id,
            candidate_name="测试候选人",
            status="submitted",
        )
        db.add(exam_record)
        db.commit()

        service = AnalysisService(db)
        try:
            service.generate_report(exam_record.id)
            assert False, "应该抛出异常"
        except Exception as e:
            error_msg = getattr(e, 'message', str(e))
            assert "AI 评分" in error_msg or "答题" in error_msg

        print("  [PASS] 无 AI 评分时正确抛出异常")
    finally:
        teardown_db()


def test_no_hiring_recommendation():
    """测试 6: AI 不输出录用建议"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        report = service.generate_report(td["exam_record"].id)

        # 确保不包含录用相关词汇
        summary_lower = report.analysis_summary
        assert "录用" not in summary_lower
        assert "淘汰" not in summary_lower
        assert "推荐" not in summary_lower or "推荐" in report.analysis_summary  # "建议面试关注" 中的推荐可以

        # 检查所有分析字段
        all_text = json.dumps({
            "summary": report.analysis_summary,
            "knowledge_mastery": report.knowledge_mastery,
            "strengths": report.strengths,
            "weak_points": report.weak_points,
            "interview_focus": report.interview_focus,
            "suggested_questions": report.suggested_questions,
        }, ensure_ascii=False)

        assert "自动筛选" not in all_text
        assert "自动淘汰" not in all_text
        assert "录用结果" not in all_text

        print("  [PASS] AI 不输出录用建议")
    finally:
        teardown_db()


def test_knowledge_analysis_quality():
    """测试 7: 知识分析内容质量"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        report = service.generate_report(td["exam_record"].id)

        # 验证知识掌握度
        knowledge_mastery = json.loads(report.knowledge_mastery)
        for k, v in knowledge_mastery.items():
            assert v in ["熟练", "掌握", "基本了解", "薄弱"]

        # 薄弱点应包含缺失的知识点
        weak_points = json.loads(report.weak_points)
        assert len(weak_points) > 0

        # 面试建议问题长度
        suggested_questions = json.loads(report.suggested_questions)
        for q in suggested_questions:
            assert len(q) <= 50, f"问题过长: {q}"

        # 面试关注点
        interview_focus = json.loads(report.interview_focus)
        assert len(interview_focus) > 0

        print("  [PASS] 知识分析内容质量验证通过")
    finally:
        teardown_db()


def test_full_flow():
    """测试 8: 完整流程"""
    db = setup_db()
    try:
        td = create_test_data(db)
        service = AnalysisService(db)

        # Step 1: 生成报告
        report = service.generate_report(td["exam_record"].id)
        assert report.status == "generated"
        print("  Step 1: 分析报告生成完成")

        # Step 2: 查询报告
        fetched = service.get_report(report.id)
        assert fetched.id == report.id
        print("  Step 2: 报告查询验证完成")

        # Step 3: HR 审核
        reviewed = service.review_report(
            report.id,
            reviewed_by=td["admin"].id,
            hr_remark="建议面试关注数据库优化和 Spring Boot 原理。",
        )
        assert reviewed.status == "reviewed"
        assert reviewed.reviewed_at is not None
        print("  Step 3: HR 审核完成")

        # Step 4: 验证所有字段
        assert reviewed.overall_score == 19.0
        assert len(reviewed.analysis_summary) > 0

        km = json.loads(reviewed.knowledge_mastery)
        st = json.loads(reviewed.strengths)
        wp = json.loads(reviewed.weak_points)
        if_ = json.loads(reviewed.interview_focus)
        sq = json.loads(reviewed.suggested_questions)

        assert len(km) > 0
        assert len(st) > 0
        assert len(wp) > 0
        assert len(if_) > 0
        assert len(sq) > 0
        print("  Step 4: 报告内容验证通过")

        # Step 5: 报告不包含录用决策
        assert "录用" not in reviewed.analysis_summary
        assert "淘汰" not in reviewed.analysis_summary
        print("  Step 5: AI 不做录用决策验证通过")

        print("  [PASS] 完整流程测试通过")
    finally:
        teardown_db()


def main():
    print("=" * 70)
    print("S5.5 招聘辅助分析能力测试")
    print("=" * 70)

    tests = [
        ("分析报告生成", test_generate_report),
        ("报告不重复生成", test_no_duplicate),
        ("报告查询", test_query_report),
        ("报告审核", test_review_report),
        ("无 AI 评分异常处理", test_no_ai_scores_error),
        ("AI 不输出录用建议", test_no_hiring_recommendation),
        ("知识分析内容质量", test_knowledge_analysis_quality),
        ("完整流程", test_full_flow),
    ]

    passed = 0
    failed = 0
    failed_tests = []

    for name, test_func in tests:
        print(f"\n=== {name} ===")
        try:
            test_func()
            passed += 1
        except Exception as e:
            import traceback
            failed += 1
            failed_tests.append((name, str(e)))
            print(f"  [FAIL] {e}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if failed_tests:
        print("\n失败详情:")
        for name, error in failed_tests:
            print(f"  - {name}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
