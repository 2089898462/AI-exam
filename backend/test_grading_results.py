"""
S3.3.3 评分结果查询测试
测试评分结果查询 Service 和 API

测试用例：
1. 评分完成查询
2. 评分处理中查询
3. 无评分记录
4. 分页查询
5. 关键词搜索
6. 状态筛选
7. 日期范围筛选
8. 详情查询
9. 详情查询（答题详情）
"""
import os
import sys

# 配置环境
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.user import User
from app.models.exam import Exam
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.models.answer_record import AnswerRecord
from app.models.grading_record import GradingRecord
from app.models.question_score_rule import QuestionScoreRule
from app.services.grading_service import GradingService


def setup_database() -> tuple[Session, object]:
    """初始化测试数据库（内存模式）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine


def cleanup_database(engine) -> None:
    """清理测试数据库"""
    try:
        Base.metadata.drop_all(engine)
        engine.dispose()
    except Exception:
        pass


def create_test_data(db: Session) -> dict:
    """创建测试数据"""
    # 创建用户
    user = User(
        username="test_hr",
        email="test@example.com",
        password_hash="hashed_password",
        display_name="测试HR",
        role="hr",
    )
    db.add(user)
    db.flush()

    # 创建考试1
    exam1 = Exam(
        title="考试A",
        description="测试考试A",
        duration_minutes=60,
        pass_score=60.0,
        status="published",
        created_by=user.id,
    )
    db.add(exam1)
    db.flush()

    # 创建考试2
    exam2 = Exam(
        title="考试B",
        description="测试考试B",
        duration_minutes=90,
        pass_score=70.0,
        status="published",
        created_by=user.id,
    )
    db.add(exam2)
    db.flush()

    # 创建题目
    question1 = Question(
        exam_id=exam1.id,
        question_no="Q1",
        type="single_choice",
        content="以下哪个是Python的基本数据类型？",
        options=["String", "Integer", "List", "All"],
        answer="D",
        score=30.0,
        sort_order=1,
    )
    db.add(question1)
    db.flush()

    question2 = Question(
        exam_id=exam1.id,
        question_no="Q2",
        type="multiple_choice",
        content="以下哪些是编程语言？",
        options=["Python", "Java", "HTML", "CSS"],
        answer="A,B",
        score=35.0,
        sort_order=2,
    )
    db.add(question2)
    db.flush()

    question3 = Question(
        exam_id=exam1.id,
        question_no="Q3",
        type="true_false",
        content="地球是圆的。",
        answer="true",
        score=35.0,
        sort_order=3,
    )
    db.add(question3)
    db.commit()

    return {
        "user": user,
        "exam1": exam1,
        "exam2": exam2,
        "question1": question1,
        "question2": question2,
        "question3": question3,
    }


def create_exam_record(db: Session, exam_id: int, candidate_name: str) -> ExamRecord:
    """创建考试记录"""
    record = ExamRecord(
        exam_id=exam_id,
        candidate_name=candidate_name,
        candidate_phone="13800138000",
        candidate_email="candidate@example.com",
        status="submitted",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_answer(db: Session, record_id: int, question_id: int, answer: str) -> AnswerRecord:
    """保存答案"""
    answer_record = AnswerRecord(
        exam_record_id=record_id,
        question_id=question_id,
        answer_content=answer,
    )
    db.add(answer_record)
    db.commit()
    db.refresh(answer_record)
    return answer_record


def create_completed_grading(db: Session, record_id: int, total_score: float, passed: bool) -> GradingRecord:
    """创建已完成的评分记录"""
    grading = GradingRecord(
        exam_record_id=record_id,
        status="completed",
        grading_type="auto",
        total_score=total_score,
        auto_score=total_score,
        passed=passed,
    )
    db.add(grading)
    db.commit()
    db.refresh(grading)
    return grading


def test_get_grading_results_pagination():
    """测试分页查询"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建多个考试记录和评分记录
        candidates = ["张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十"]
        records = []
        for i, name in enumerate(candidates):
            record = create_exam_record(db, test_data["exam1"].id, name)
            records.append(record)
            # 添加答案
            save_answer(db, record.id, test_data["question1"].id, "D")
            save_answer(db, record.id, test_data["question2"].id, "A,B")
            save_answer(db, record.id, test_data["question3"].id, "true")
            # 创建评分记录
            score = 100.0 if i % 2 == 0 else 50.0
            create_completed_grading(db, record.id, score, score >= 60)

        grading_service = GradingService(db)

        # 测试第一页，每页3条
        result = grading_service.get_grading_results(page=1, page_size=3)
        assert len(result["items"]) == 3, f"期望3条，实际{len(result['items'])}"
        assert result["total"] == 8, f"期望总数8，实际{result['total']}"
        assert result["page"] == 1
        assert result["page_size"] == 3

        # 测试第二页
        result = grading_service.get_grading_results(page=2, page_size=3)
        assert len(result["items"]) == 3, f"期望3条，实际{len(result['items'])}"

        # 测试最后一页
        result = grading_service.get_grading_results(page=3, page_size=3)
        assert len(result["items"]) == 2, f"期望2条，实际{len(result['items'])}"

        print("✅ test_get_grading_results_pagination 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_completed():
    """测试评分完成查询"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建已完成评分的记录
        record = create_exam_record(db, test_data["exam1"].id, "张三")
        save_answer(db, record.id, test_data["question1"].id, "D")
        grading = create_completed_grading(db, record.id, 100.0, True)

        grading_service = GradingService(db)
        result = grading_service.get_grading_results(page=1, page_size=10)

        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["status"] == "completed"
        assert item["total_score"] == 100.0
        assert item["passed"] == True
        assert item["candidate_name"] == "张三"

        print("✅ test_get_grading_results_completed 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_processing():
    """测试评分处理中查询"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建评分中的记录
        record = create_exam_record(db, test_data["exam1"].id, "李四")
        grading = GradingRecord(
            exam_record_id=record.id,
            status="grading",
            grading_type="auto",
        )
        db.add(grading)
        db.commit()

        grading_service = GradingService(db)
        result = grading_service.get_grading_results(page=1, page_size=10, status="grading")

        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "grading"

        print("✅ test_get_grading_results_processing 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_no_records():
    """测试无评分记录"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        grading_service = GradingService(db)
        result = grading_service.get_grading_results(page=1, page_size=10)

        assert len(result["items"]) == 0
        assert result["total"] == 0

        print("✅ test_get_grading_results_no_records 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_keyword_search():
    """测试关键词搜索"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建多个候选人
        candidates = [
            ("张三", "13800000001", "zhangsan@test.com"),
            ("李四", "13800000002", "lisi@test.com"),
            ("王五", "13800000003", "wangwu@test.com"),
        ]
        for name, phone, email in candidates:
            record = ExamRecord(
                exam_id=test_data["exam1"].id,
                candidate_name=name,
                candidate_phone=phone,
                candidate_email=email,
                status="submitted",
            )
            db.add(record)
            db.flush()
            create_completed_grading(db, record.id, 80.0, True)

        db.commit()

        grading_service = GradingService(db)

        # 按姓名搜索
        result = grading_service.get_grading_results(page=1, page_size=10, keyword="张三")
        assert len(result["items"]) == 1
        assert result["items"][0]["candidate_name"] == "张三"

        # 按手机搜索
        result = grading_service.get_grading_results(page=1, page_size=10, keyword="13800000002")
        assert len(result["items"]) == 1
        assert result["items"][0]["candidate_name"] == "李四"

        # 按邮箱搜索
        result = grading_service.get_grading_results(page=1, page_size=10, keyword="wangwu")
        assert len(result["items"]) == 1
        assert result["items"][0]["candidate_name"] == "王五"

        print("✅ test_get_grading_results_keyword_search 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_status_filter():
    """测试状态筛选"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建不同状态的记录
        record1 = create_exam_record(db, test_data["exam1"].id, "候选人A")
        create_completed_grading(db, record1.id, 80.0, True)

        record2 = create_exam_record(db, test_data["exam1"].id, "候选人B")
        grading2 = GradingRecord(
            exam_record_id=record2.id,
            status="grading",
            grading_type="auto",
        )
        db.add(grading2)
        db.commit()

        record3 = create_exam_record(db, test_data["exam1"].id, "候选人C")
        grading3 = GradingRecord(
            exam_record_id=record3.id,
            status="pending",
            grading_type="auto",
        )
        db.add(grading3)
        db.commit()

        grading_service = GradingService(db)

        # 筛选已完成
        result = grading_service.get_grading_results(page=1, page_size=10, status="completed")
        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "completed"

        # 筛选评分中
        result = grading_service.get_grading_results(page=1, page_size=10, status="grading")
        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "grading"

        # 筛选待评分
        result = grading_service.get_grading_results(page=1, page_size=10, status="pending")
        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "pending"

        print("✅ test_get_grading_results_status_filter 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_result_detail():
    """测试详情查询"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 创建记录和答案
        record = create_exam_record(db, test_data["exam1"].id, "张三")
        answer1 = save_answer(db, record.id, test_data["question1"].id, "D")
        answer2 = save_answer(db, record.id, test_data["question2"].id, "A,B")
        answer3 = save_answer(db, record.id, test_data["question3"].id, "true")

        # 更新答案评分
        answer1.score = 30.0
        answer1.is_correct = True
        answer2.score = 35.0
        answer2.is_correct = True
        answer3.score = 35.0
        answer3.is_correct = True
        db.commit()

        # 创建评分记录
        create_completed_grading(db, record.id, 100.0, True)

        grading_service = GradingService(db)
        detail = grading_service.get_grading_result_detail(record.id)

        # 验证基本信息
        assert detail["candidate_name"] == "张三"
        assert detail["exam_title"] == "考试A"
        assert detail["total_score"] == 100.0
        assert detail["passed"] == True

        # 验证统计信息
        assert detail["statistics"]["total_questions"] == 3
        assert detail["statistics"]["answered_count"] == 3
        assert detail["statistics"]["correct_count"] == 3
        assert detail["statistics"]["correct_rate"] == 100.0

        # 验证答题详情
        assert len(detail["answers"]) == 3
        answer_detail = detail["answers"][0]
        assert answer_detail["score"] == 30.0
        assert answer_detail["is_correct"] == True

        print("✅ test_get_grading_result_detail 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_result_detail_not_found():
    """测试详情查询 - 评分记录不存在"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        grading_service = GradingService(db)

        try:
            grading_service.get_grading_result_detail(999)
            assert False, "应该抛出异常"
        except Exception as e:
            assert "评分记录不存在" in str(e)

        print("✅ test_get_grading_result_detail_not_found 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_results_exam_filter():
    """测试按考试筛选"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        # 为两个考试创建记录
        record1 = create_exam_record(db, test_data["exam1"].id, "考试A候选人")
        create_completed_grading(db, record1.id, 90.0, True)

        record2 = create_exam_record(db, test_data["exam2"].id, "考试B候选人")
        create_completed_grading(db, record2.id, 75.0, True)

        grading_service = GradingService(db)

        # 筛选考试A
        result = grading_service.get_grading_results(
            page=1, page_size=10, exam_id=test_data["exam1"].id
        )
        assert len(result["items"]) == 1
        assert result["items"][0]["candidate_name"] == "考试A候选人"
        assert result["items"][0]["exam_id"] == test_data["exam1"].id

        # 筛选考试B
        result = grading_service.get_grading_results(
            page=1, page_size=10, exam_id=test_data["exam2"].id
        )
        assert len(result["items"]) == 1
        assert result["items"][0]["candidate_name"] == "考试B候选人"

        print("✅ test_get_grading_results_exam_filter 通过")
    finally:
        db.close()
        cleanup_database(engine)


def test_get_grading_result_detail_with_wrong_answers():
    """测试详情查询 - 部分错误答案"""
    db, engine = setup_database()
    try:
        test_data = create_test_data(db)

        record = create_exam_record(db, test_data["exam1"].id, "李四")
        answer1 = save_answer(db, record.id, test_data["question1"].id, "A")  # 错误
        answer2 = save_answer(db, record.id, test_data["question2"].id, "A,B")  # 正确
        answer3 = save_answer(db, record.id, test_data["question3"].id, "false")  # 错误

        # 更新答案评分
        answer1.score = 0.0
        answer1.is_correct = False
        answer2.score = 35.0
        answer2.is_correct = True
        answer3.score = 0.0
        answer3.is_correct = False
        db.commit()

        create_completed_grading(db, record.id, 35.0, False)

        grading_service = GradingService(db)
        detail = grading_service.get_grading_result_detail(record.id)

        assert detail["total_score"] == 35.0
        assert detail["passed"] == False
        assert detail["statistics"]["correct_count"] == 1
        assert detail["statistics"]["correct_rate"] == 33.3

        # 验证答题详情中的错误标记
        wrong_answers = [a for a in detail["answers"] if a["is_correct"] == False]
        assert len(wrong_answers) == 2

        print("✅ test_get_grading_result_detail_with_wrong_answers 通过")
    finally:
        db.close()
        cleanup_database(engine)


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("S3.3.3 评分结果查询测试")
    print("=" * 60)
    print()

    errors = []

    tests = [
        ("分页查询", test_get_grading_results_pagination),
        ("评分完成查询", test_get_grading_results_completed),
        ("评分处理中查询", test_get_grading_results_processing),
        ("无评分记录", test_get_grading_results_no_records),
        ("关键词搜索", test_get_grading_results_keyword_search),
        ("状态筛选", test_get_grading_results_status_filter),
        ("详情查询", test_get_grading_result_detail),
        ("详情查询-不存在", test_get_grading_result_detail_not_found),
        ("按考试筛选", test_get_grading_results_exam_filter),
        ("详情-部分错误", test_get_grading_result_detail_with_wrong_answers),
    ]

    print("📋 评分结果查询测试")
    print("-" * 40)
    for name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()
    print("=" * 60)
    total = len(tests)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")
    print("=" * 60)

    if errors:
        print("\n❌ 失败的测试：")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return 1
    else:
        print("\n🎉 所有测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
