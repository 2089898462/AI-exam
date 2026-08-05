"""
AnswerRecordService 单元测试
使用 SQLite 内存数据库
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import User, Exam, Question, ExamRecord, AnswerRecord, AiReport
from app.exceptions import BusinessException, NotFoundException, ValidationException
from app.services.answer_record_service import AnswerRecordService
from app.services.exam_record_service import ExamRecordService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def exam_with_questions(db_session):
    user = User(
        username="hr_test",
        password_hash="hashed",
        display_name="HR",
        role="hr",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    exam = Exam(
        title="答题测试考试",
        duration_minutes=30,
        status="published",
        created_by=user.id,
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)

    questions = []
    for i in range(3):
        q = Question(
            exam_id=exam.id,
            type="single_choice",
            content=f"题目 {i + 1}",
            options=[{"label": "A", "content": "选项A"}, {"label": "B", "content": "选项B"}],
            answer="A",
            score=10.0,
            sort_order=i,
        )
        db_session.add(q)
        questions.append(q)
    db_session.commit()
    return exam, questions


@pytest.fixture
def exam_record_in_progress(db_session, exam_with_questions):
    exam, questions = exam_with_questions
    svc = ExamRecordService(db_session)
    record = svc.create_exam_record(
        exam_id=exam.id, candidate_name="张三"
    )
    svc.start_exam(record.id)
    return record, questions


class TestSaveAnswer:
    def test_save_new_answer(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        answer = svc.save_answer(
            record_id=record.id,
            question_id=questions[0].id,
            answer_content="A",
        )
        assert answer.id is not None
        assert answer.exam_record_id == record.id
        assert answer.question_id == questions[0].id
        assert answer.answer_content == "A"

    def test_save_idempotent_update(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        a1 = svc.save_answer(record.id, questions[0].id, "A")
        a2 = svc.save_answer(record.id, questions[0].id, "B")
        assert a1.id == a2.id
        assert a2.answer_content == "B"

    def test_save_record_not_found(self, db_session):
        svc = AnswerRecordService(db_session)
        with pytest.raises(NotFoundException) as exc:
            svc.save_answer(record_id=999, question_id=1, answer_content="A")
        assert "考试记录不存在" in str(exc.value.message)

    def test_save_question_not_found(self, db_session, exam_record_in_progress):
        record, _ = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        with pytest.raises(NotFoundException) as exc:
            svc.save_answer(record_id=record.id, question_id=999, answer_content="A")
        assert "题目不存在" in str(exc.value.message)

    def test_save_question_wrong_exam(self, db_session, exam_with_questions):
        exam, questions = exam_with_questions
        svc_exam = ExamRecordService(db_session)
        record = svc_exam.create_exam_record(exam_id=exam.id, candidate_name="李四")
        svc_exam.start_exam(record.id)

        other_exam = Exam(
            title="其他考试",
            duration_minutes=30,
            status="published",
            created_by=1,
        )
        db_session.add(other_exam)
        db_session.commit()
        db_session.refresh(other_exam)

        other_q = Question(
            exam_id=other_exam.id,
            type="single_choice",
            content="其他考试的题目",
            answer="A",
            score=10.0,
            sort_order=0,
        )
        db_session.add(other_q)
        db_session.commit()

        svc = AnswerRecordService(db_session)
        with pytest.raises(ValidationException) as exc:
            svc.save_answer(
                record_id=record.id,
                question_id=other_q.id,
                answer_content="A",
            )
        assert "不属于该考试" in str(exc.value.message)

    def test_save_after_submit(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc_exam = ExamRecordService(db_session)
        svc_exam.submit_exam(record.id)

        svc = AnswerRecordService(db_session)
        with pytest.raises(BusinessException) as exc:
            svc.save_answer(record.id, questions[0].id, "A")
        assert "无法修改答案" in str(exc.value.message)


class TestSaveAnswersBatch:
    def test_batch_save_success(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)

        answers = [
            {"question_id": questions[0].id, "answer_content": "A"},
            {"question_id": questions[1].id, "answer_content": "B"},
            {"question_id": questions[2].id, "answer_content": "C"},
        ]
        saved = svc.save_answers_batch(record.id, answers)
        assert len(saved) == 3

        for i, a in enumerate(saved):
            assert a.question_id == questions[i].id
            assert a.answer_content == ["A", "B", "C"][i]

    def test_batch_empty_list(self, db_session, exam_record_in_progress):
        record, _ = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        with pytest.raises(ValidationException) as exc:
            svc.save_answers_batch(record.id, [])
        assert "答案列表不能为空" in str(exc.value.message)

    def test_batch_missing_question_id(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        with pytest.raises(ValidationException) as exc:
            svc.save_answers_batch(record.id, [{"answer_content": "A"}])
        assert "缺少 question_id" in str(exc.value.message)

    def test_batch_partial_update(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)

        svc.save_answers_batch(record.id, [
            {"question_id": questions[0].id, "answer_content": "A"},
        ])
        svc.save_answers_batch(record.id, [
            {"question_id": questions[0].id, "answer_content": "A_new"},
            {"question_id": questions[1].id, "answer_content": "B"},
        ])

        answers = svc.get_answers_by_record(record.id)
        assert len(answers) == 2

    def test_batch_after_submit(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc_exam = ExamRecordService(db_session)
        svc_exam.submit_exam(record.id)

        svc = AnswerRecordService(db_session)
        with pytest.raises(BusinessException) as exc:
            svc.save_answers_batch(record.id, [
                {"question_id": questions[0].id, "answer_content": "A"},
            ])
        assert "无法提交答案" in str(exc.value.message)


class TestGetAnswersByRecord:
    def test_get_answers_success(self, db_session, exam_record_in_progress):
        record, questions = exam_record_in_progress
        svc = AnswerRecordService(db_session)

        svc.save_answer(record.id, questions[0].id, "A")
        svc.save_answer(record.id, questions[1].id, "B")

        answers = svc.get_answers_by_record(record.id)
        assert len(answers) == 2
        assert answers[0].question_id == questions[0].id
        assert answers[1].question_id == questions[1].id

    def test_get_answers_empty(self, db_session, exam_record_in_progress):
        record, _ = exam_record_in_progress
        svc = AnswerRecordService(db_session)
        answers = svc.get_answers_by_record(record.id)
        assert len(answers) == 0

    def test_get_answers_record_not_found(self, db_session):
        svc = AnswerRecordService(db_session)
        with pytest.raises(NotFoundException) as exc:
            svc.get_answers_by_record(999)
        assert "考试记录不存在" in str(exc.value.message)
