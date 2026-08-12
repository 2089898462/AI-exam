"""
S3.3.2 客观题自动评分测试
测试客观题评分模块和评分服务

测试用例：
1. 单选题评分（正确/错误）
2. 多选题评分（匹配/错误）
3. 判断题评分（正确/错误）
4. 空答案处理
5. 重复评分防止
6. 完整自动评分流程
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
from app.services.objective_grader import (
    grade_question,
    is_objective_question,
    calculate_auto_score,
    _normalize_answer,
)

# 全局变量用于管理数据库连接
_engines = []


def setup_database() -> tuple[Session, object]:
    """初始化测试数据库（内存模式）"""
    engine = create_engine("sqlite:///:memory:")
    _engines.append(engine)
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


def create_test_data(db: Session):
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

    # 创建考试
    exam = Exam(
        title="测试考试",
        description="客观题评分测试",
        duration_minutes=60,
        pass_score=60.0,
        status="published",
        created_by=user.id,
    )
    db.add(exam)
    db.flush()

    # 创建题目 - 单选题
    question1 = Question(
        exam_id=exam.id,
        question_no="Q1",
        type="single_choice",
        content="以下哪个是Python的基本数据类型？",
        options=["String", "Integer", "List", "All"],
        answer="D",
        score=30.0,
        sort_order=1,
    )
    db.add(question1)

    # 创建题目 - 单选题（简单）
    question2 = Question(
        exam_id=exam.id,
        question_no="Q2",
        type="single_choice",
        content="1 + 1 等于？",
        options=["1", "2", "3", "4"],
        answer="B",
        score=30.0,
        sort_order=2,
    )
    db.add(question2)

    # 创建题目 - 多选题
    question3 = Question(
        exam_id=exam.id,
        question_no="Q3",
        type="multiple_choice",
        content="以下哪些是编程语言？",
        options=["Python", "Java", "HTML", "CSS"],
        answer="A,B",
        score=20.0,
        sort_order=3,
    )
    db.add(question3)

    # 创建题目 - 判断题
    question4 = Question(
        exam_id=exam.id,
        question_no="Q4",
        type="true_false",
        content="地球是圆的。",
        answer="true",
        score=20.0,
        sort_order=4,
    )
    db.add(question4)

    db.commit()
    return user, exam


def create_exam_record(db: Session, exam_id: int, candidate_name: str) -> ExamRecord:
    """创建考试记录"""
    record = ExamRecord(
        exam_id=exam_id,
        candidate_name=candidate_name,
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


# ============================================================
# 单元测试：ObjectiveGrader 模块
# ============================================================

def test_single_choice_correct():
    """测试单选题正确"""
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer="D",
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 10.0, f"期望得分 10.0，实际 {score}"
    assert is_correct == True, "期望正确"
    print("✅ test_single_choice_correct 通过")


def test_single_choice_wrong():
    """测试单选题错误"""
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer="A",
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 0.0, f"期望得分 0.0，实际 {score}"
    assert is_correct == False, "期望错误"
    print("✅ test_single_choice_wrong 通过")


def test_single_choice_case_insensitive():
    """测试单选题忽略大小写"""
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer="d",
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 10.0, f"期望得分 10.0，实际 {score}"
    assert is_correct == True, "期望正确（忽略大小写）"
    print("✅ test_single_choice_case_insensitive 通过")


def test_multiple_choice_exact_match():
    """测试多选题完全匹配"""
    score, is_correct = grade_question(
        question_type="multiple_choice",
        candidate_answer="A,B",
        standard_answer="A,B",
        full_score=20.0,
    )
    assert score == 20.0, f"期望得分 20.0，实际 {score}"
    assert is_correct == True, "期望正确"
    print("✅ test_multiple_choice_exact_match 通过")


def test_multiple_choice_different_order():
    """测试多选题顺序不同"""
    score, is_correct = grade_question(
        question_type="multiple_choice",
        candidate_answer="B,A",
        standard_answer="A,B",
        full_score=20.0,
    )
    assert score == 20.0, f"期望得分 20.0，实际 {score}"
    assert is_correct == True, "期望正确（顺序无关）"
    print("✅ test_multiple_choice_different_order 通过")


def test_multiple_choice_partial_match():
    """测试多选题部分匹配"""
    score, is_correct = grade_question(
        question_type="multiple_choice",
        candidate_answer="A",
        standard_answer="A,B",
        full_score=20.0,
    )
    assert score == 0.0, f"期望得分 0.0（多选必须全对），实际 {score}"
    assert is_correct == False, "期望错误（部分选择不算正确）"
    print("✅ test_multiple_choice_partial_match 通过")


def test_multiple_choice_wrong():
    """测试多选题错误"""
    score, is_correct = grade_question(
        question_type="multiple_choice",
        candidate_answer="C,D",
        standard_answer="A,B",
        full_score=20.0,
    )
    assert score == 0.0, f"期望得分 0.0，实际 {score}"
    assert is_correct == False, "期望错误"
    print("✅ test_multiple_choice_wrong 通过")


def test_multiple_choice_json_format():
    """测试多选题 JSON 格式"""
    score, is_correct = grade_question(
        question_type="multiple_choice",
        candidate_answer='["A", "B"]',
        standard_answer="A,B",
        full_score=20.0,
    )
    assert score == 20.0, f"期望得分 20.0，实际 {score}"
    assert is_correct == True, "期望正确（支持 JSON 格式）"
    print("✅ test_multiple_choice_json_format 通过")


def test_true_false_correct():
    """测试判断题正确"""
    # 答案为 "true"
    score, is_correct = grade_question(
        question_type="true_false",
        candidate_answer="true",
        standard_answer="true",
        full_score=5.0,
    )
    assert score == 5.0, f"期望得分 5.0，实际 {score}"
    assert is_correct == True, "期望正确"

    # 答案为 "false"
    score, is_correct = grade_question(
        question_type="true_false",
        candidate_answer="false",
        standard_answer="false",
        full_score=5.0,
    )
    assert score == 5.0, f"期望得分 5.0，实际 {score}"
    assert is_correct == True, "期望正确"
    print("✅ test_true_false_correct 通过")


def test_true_false_chinese():
    """测试判断题中文答案"""
    # 中文 "正确"
    score, is_correct = grade_question(
        question_type="true_false",
        candidate_answer="正确",
        standard_answer="true",
        full_score=5.0,
    )
    assert score == 5.0, f"期望得分 5.0，实际 {score}"
    assert is_correct == True, "期望正确（支持中文'正确'）"

    # 中文 "错误"
    score, is_correct = grade_question(
        question_type="true_false",
        candidate_answer="错误",
        standard_answer="false",
        full_score=5.0,
    )
    assert score == 5.0, f"期望得分 5.0，实际 {score}"
    assert is_correct == True, "期望正确（支持中文'错误'）"
    print("✅ test_true_false_chinese 通过")


def test_true_false_wrong():
    """测试判断题错误"""
    score, is_correct = grade_question(
        question_type="true_false",
        candidate_answer="true",
        standard_answer="false",
        full_score=5.0,
    )
    assert score == 0.0, f"期望得分 0.0，实际 {score}"
    assert is_correct == False, "期望错误"
    print("✅ test_true_false_wrong 通过")


def test_empty_answer():
    """测试空答案"""
    # 空字符串
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer="",
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 0.0, f"空答案期望得分 0.0，实际 {score}"
    assert is_correct == False, "空答案期望错误"

    # None
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer=None,
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 0.0, f"None答案期望得分 0.0，实际 {score}"
    assert is_correct == False, "None答案期望错误"

    # 空格
    score, is_correct = grade_question(
        question_type="single_choice",
        candidate_answer="   ",
        standard_answer="D",
        full_score=10.0,
    )
    assert score == 0.0, f"空格答案期望得分 0.0，实际 {score}"
    assert is_correct == False, "空格答案期望错误"
    print("✅ test_empty_answer 通过")


def test_not_objective_question():
    """测试非客观题"""
    assert is_objective_question("single_choice") == True
    assert is_objective_question("multiple_choice") == True
    assert is_objective_question("true_false") == True
    assert is_objective_question("short_answer") == False
    assert is_objective_question("unknown_type") == False

    # 非客观题不评分
    score, is_correct = grade_question(
        question_type="short_answer",
        candidate_answer="任意内容",
        standard_answer="标准答案",
        full_score=20.0,
    )
    assert score == 0.0, f"非客观题期望得分 0.0，实际 {score}"
    assert is_correct == False, "非客观题不参与评分"
    print("✅ test_not_objective_question 通过")


def test_normalize_answer():
    """测试答案规范化"""
    # 单选格式
    assert _normalize_answer("A") == "A"

    # 逗号分隔
    assert _normalize_answer("A,B,C") == "A,B,C"

    # 空格分隔
    result = _normalize_answer("A B C")
    assert result == "A,B,C", f"期望 'A,B,C'，实际 '{result}'"

    # JSON 格式
    result = _normalize_answer('["A", "B", "C"]')
    assert result == "A,B,C", f"期望 'A,B,C'，实际 '{result}'"

    # 无序
    result = _normalize_answer("C,A,B")
    assert result == "A,B,C", f"期望 'A,B,C'（排序后），实际 '{result}'"

    # 重复选项
    result = _normalize_answer("A,A,B")
    assert result == "A,B", f"期望 'A,B'（去重后），实际 '{result}'"

    # 空
    assert _normalize_answer("") == ""
    assert _normalize_answer(None) == ""
    print("✅ test_normalize_answer 通过")


# ============================================================
# 集成测试：GradingService 自动评分流程
# ============================================================

def test_full_auto_grading_flow():
    """测试完整自动评分流程
    
    场景：候选人提交答案后，执行自动评分
    """
    db, engine = setup_database()
    try:
        # 创建测试数据
        user, exam = create_test_data(db)

        # 创建考试记录
        record = create_exam_record(db, exam.id, "张三")

        # 保存答案 - 全对
        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        q2 = db.query(Question).filter(Question.question_no == "Q2").first()
        q3 = db.query(Question).filter(Question.question_no == "Q3").first()
        q4 = db.query(Question).filter(Question.question_no == "Q4").first()

        save_answer(db, record.id, q1.id, "D")      # 正确 +30
        save_answer(db, record.id, q2.id, "B")      # 正确 +30
        save_answer(db, record.id, q3.id, "A,B")    # 正确 +20
        save_answer(db, record.id, q4.id, "true")   # 正确 +20

        # 执行自动评分
        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        # 验证评分结果
        assert grading.status == "completed", f"状态应为 completed，实际 {grading.status}"
        assert grading.total_score == 100.0, f"期望总分 100.0，实际 {grading.total_score}"
        assert grading.auto_score == 100.0, f"期望客观题得分 100.0，实际 {grading.auto_score}"
        assert grading.passed == True, f"期望及格 True，实际 {grading.passed}"
        assert grading.completed_at is not None, "应有完成时间"

        # 验证答题记录评分
        answers = db.query(AnswerRecord).filter(
            AnswerRecord.exam_record_id == record.id
        ).all()
        for answer in answers:
            assert answer.score is not None, f"答题记录 {answer.id} 应有分数"
            assert answer.is_correct == True, f"答题记录 {answer.id} 应为正确"

        # 验证考试记录状态
        db.refresh(record)
        assert record.status == "graded", f"考试记录状态应为 graded，实际 {record.status}"

        print("✅ test_full_auto_grading_flow 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_auto_grading_with_wrong_answers():
    """测试错误答案评分"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "李四")

        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        q2 = db.query(Question).filter(Question.question_no == "Q2").first()
        q3 = db.query(Question).filter(Question.question_no == "Q3").first()
        q4 = db.query(Question).filter(Question.question_no == "Q4").first()

        save_answer(db, record.id, q1.id, "A")      # 错误 +0
        save_answer(db, record.id, q2.id, "A")      # 错误 +0
        save_answer(db, record.id, q3.id, "C,D")    # 错误 +0
        save_answer(db, record.id, q4.id, "false")  # 错误 +0

        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        assert grading.status == "completed"
        assert grading.total_score == 0.0, f"期望总分 0.0，实际 {grading.total_score}"
        assert grading.passed == False, f"期望不及格 False，实际 {grading.passed}"

        print("✅ test_auto_grading_with_wrong_answers 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_auto_grading_with_empty_answers():
    """测试空答案处理"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "王五")

        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        q2 = db.query(Question).filter(Question.question_no == "Q2").first()

        # 空答案
        save_answer(db, record.id, q1.id, "")
        save_answer(db, record.id, q2.id, None)

        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        assert grading.status == "completed"
        assert grading.total_score == 0.0, f"空答案期望总分 0.0，实际 {grading.total_score}"
        assert grading.passed == False

        print("✅ test_auto_grading_with_empty_answers 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_auto_grading_with_partial_answers():
    """测试部分答对"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "赵六")

        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        q2 = db.query(Question).filter(Question.question_no == "Q2").first()
        q3 = db.query(Question).filter(Question.question_no == "Q3").first()
        q4 = db.query(Question).filter(Question.question_no == "Q4").first()

        save_answer(db, record.id, q1.id, "D")      # 正确 +30
        save_answer(db, record.id, q2.id, "A")      # 错误 +0
        save_answer(db, record.id, q3.id, "A,B")    # 正确 +20
        save_answer(db, record.id, q4.id, "false")  # 错误 +0

        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        assert grading.status == "completed"
        assert grading.total_score == 50.0, f"期望总分 50.0，实际 {grading.total_score}"
        assert grading.auto_score == 50.0

        print("✅ test_auto_grading_with_partial_answers 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_duplicate_grading_prevention():
    """测试重复评分防止"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "孙七")

        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        save_answer(db, record.id, q1.id, "D")

        grading_service = GradingService(db)

        # 第一次评分
        grading1 = grading_service.auto_grade_exam(record.id)
        assert grading1.status == "completed"
        assert grading1.total_score == 30.0

        # 第二次评分应该抛出异常
        try:
            grading2 = grading_service.auto_grade_exam(record.id)
            assert False, "应该抛出重复评分异常"
        except Exception as e:
            assert "评分已完成" in str(e), f"错误信息应为评分已完成，实际：{e}"

        print("✅ test_duplicate_grading_prevention 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_auto_grading_without_answers():
    """测试无答案的自动评分"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "周八")

        # 没有保存任何答案

        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        assert grading.status == "completed"
        assert grading.total_score == 0.0
        assert grading.auto_score == 0.0

        print("✅ test_auto_grading_without_answers 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_grading_status_query():
    """测试评分状态查询"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)
        record = create_exam_record(db, exam.id, "吴九")

        grading_service = GradingService(db)

        # 未评分状态
        status = grading_service.get_grading_status(record.id)
        assert status["exists"] == False
        assert status["status"] == "not_started"

        # 创建评分记录
        grading_service.create_grading_record(record.id)

        status = grading_service.get_grading_status(record.id)
        assert status["exists"] == True
        assert status["status"] == "pending"

        print("✅ test_grading_status_query 通过")

    finally:
        db.close()
        cleanup_database(engine)


def test_grade_with_custom_pass_score():
    """测试自定义及格分数线"""
    db, engine = setup_database()
    try:
        user, exam = create_test_data(db)

        # 为考试设置及格分数线（从评分规则）
        rule = QuestionScoreRule(
            exam_id=exam.id,
            question_type="single_choice",
            score_method="auto_compare",
            pass_score=40.0,
            weight=1.0,
            is_enabled=True,
        )
        db.add(rule)
        db.commit()

        record = create_exam_record(db, exam.id, "郑十")

        q1 = db.query(Question).filter(Question.question_no == "Q1").first()
        save_answer(db, record.id, q1.id, "D")  # 30分

        grading_service = GradingService(db)
        grading = grading_service.auto_grade_exam(record.id)

        # 得分 30 < 及格线 40，应为不及格
        assert grading.total_score == 30.0
        assert grading.passed == False, f"30分 < 40分及格线，应为不及格"

        print("✅ test_grade_with_custom_pass_score 通过")

    finally:
        db.close()
        cleanup_database(engine)


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("S3.3.2 客观题自动评分测试")
    print("=" * 60)
    print()

    errors = []

    # 单元测试：ObjectiveGrader
    unit_tests = [
        ("单选题正确", test_single_choice_correct),
        ("单选题错误", test_single_choice_wrong),
        ("单选题忽略大小写", test_single_choice_case_insensitive),
        ("多选题完全匹配", test_multiple_choice_exact_match),
        ("多选题顺序无关", test_multiple_choice_different_order),
        ("多选题部分匹配", test_multiple_choice_partial_match),
        ("多选题错误", test_multiple_choice_wrong),
        ("多选题JSON格式", test_multiple_choice_json_format),
        ("判断题正确", test_true_false_correct),
        ("判断题中文答案", test_true_false_chinese),
        ("判断题错误", test_true_false_wrong),
        ("空答案处理", test_empty_answer),
        ("非客观题识别", test_not_objective_question),
        ("答案规范化", test_normalize_answer),
    ]

    print("📋 单元测试：ObjectiveGrader 评分模块")
    print("-" * 40)
    for name, test_func in unit_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()

    # 集成测试：GradingService
    integration_tests = [
        ("完整自动评分流程", test_full_auto_grading_flow),
        ("错误答案评分", test_auto_grading_with_wrong_answers),
        ("空答案处理", test_auto_grading_with_empty_answers),
        ("部分答对", test_auto_grading_with_partial_answers),
        ("重复评分防止", test_duplicate_grading_prevention),
        ("无答案评分", test_auto_grading_without_answers),
        ("评分状态查询", test_grading_status_query),
        ("自定义及格线", test_grade_with_custom_pass_score),
    ]

    print("📋 集成测试：GradingService 评分流程")
    print("-" * 40)
    for name, test_func in integration_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()
    print("=" * 60)
    total = len(unit_tests) + len(integration_tests)
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
