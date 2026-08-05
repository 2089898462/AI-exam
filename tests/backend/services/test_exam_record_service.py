"""
ExamRecordService 单元测试
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
from app.exceptions import BusinessException, NotFoundException
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
def sample_exam(db_session):
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
        title="S3.1.2 测试考试",
        duration_minutes=30,
        status="published",
        created_by=user.id,
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)

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
    db_session.commit()
    return exam


class TestCreateExamRecord:
    def test_create_success(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id,
            candidate_name="张三",
            candidate_phone="13800138000",
            candidate_email="zhangsan@test.com",
        )
        assert record.id is not None
        assert record.exam_id == sample_exam.id
        assert record.candidate_name == "张三"
        assert record.status == "not_started"
        assert record.started_at is not None

    def test_create_exam_not_found(self, db_session):
        svc = ExamRecordService(db_session)
        with pytest.raises(NotFoundException) as exc:
            svc.create_exam_record(exam_id=999, candidate_name="张三")
        assert "考试不存在" in str(exc.value.message)

    def test_create_empty_name(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        with pytest.raises(BusinessException) as exc:
            svc.create_exam_record(
                exam_id=sample_exam.id,
                candidate_name="  ",
            )
        assert "候选人姓名不能为空" in str(exc.value.message)


class TestGetRecordById:
    def test_get_success(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        created = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        record = svc.get_record_by_id(created.id)
        assert record.id == created.id
        assert record.candidate_name == "张三"

    def test_get_not_found(self, db_session):
        svc = ExamRecordService(db_session)
        with pytest.raises(NotFoundException) as exc:
            svc.get_record_by_id(999)
        assert "考试记录不存在" in str(exc.value.message)


class TestStartExam:
    def test_start_success(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        started = svc.start_exam(record.id)
        assert started.status == "in_progress"
        assert started.started_at is not None

    def test_start_already_in_progress(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        svc.start_exam(record.id)
        with pytest.raises(BusinessException) as exc:
            svc.start_exam(record.id)
        assert "无法开始" in str(exc.value.message)


class TestSubmitExam:
    def test_submit_success(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        svc.start_exam(record.id)
        submitted = svc.submit_exam(record.id)
        assert submitted.status == "submitted"
        assert submitted.submitted_at is not None

    def test_submit_not_started(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        with pytest.raises(BusinessException) as exc:
            svc.submit_exam(record.id)
        assert "无法提交" in str(exc.value.message)

    def test_submit_already_submitted(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        svc.start_exam(record.id)
        svc.submit_exam(record.id)
        with pytest.raises(BusinessException) as exc:
            svc.submit_exam(record.id)
        assert "无法提交" in str(exc.value.message)


class TestListExamRecords:
    def test_list_by_exam(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        svc.create_exam_record(exam_id=sample_exam.id, candidate_name="张三")
        svc.create_exam_record(exam_id=sample_exam.id, candidate_name="李四")

        records = svc.list_exam_records(exam_id=sample_exam.id)
        assert len(records) == 2

    def test_list_empty(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        records = svc.list_exam_records(exam_id=sample_exam.id)
        assert len(records) == 0

    def test_list_by_status(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        r1 = svc.create_exam_record(exam_id=sample_exam.id, candidate_name="张三")
        svc.start_exam(r1.id)
        svc.submit_exam(r1.id)
        svc.create_exam_record(exam_id=sample_exam.id, candidate_name="李四")

        submitted = svc.list_exam_records(exam_id=sample_exam.id, status="submitted")
        assert len(submitted) == 1
        assert submitted[0].candidate_name == "张三"

        not_started = svc.list_exam_records(exam_id=sample_exam.id, status="not_started")
        assert len(not_started) == 1
        assert not_started[0].candidate_name == "李四"


class TestGetDetailWithAnswers:
    def test_get_detail(self, db_session, sample_exam):
        svc = ExamRecordService(db_session)
        record = svc.create_exam_record(
            exam_id=sample_exam.id, candidate_name="张三"
        )
        detail = svc.get_detail_with_answers(record.id)
        assert detail.id == record.id
        assert len(detail.answer_records) == 0
        assert detail.exam is not None
