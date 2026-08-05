"""
考试记录 API 端点测试
使用 SQLite 内存数据库 + FastAPI TestClient
使用 StaticPool 确保所有连接共享同一内存数据库
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Exam, Question, User
from main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session, TestingSessionLocal, engine
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    session, TestingSessionLocal, engine = db_session

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(db_session):
    session, _, _ = db_session

    hr_user = User(
        username="hr_test",
        password_hash=hash_password("testpass123"),
        display_name="HR Test",
        role="hr",
        status="active",
    )
    session.add(hr_user)
    session.commit()
    session.refresh(hr_user)

    exam = Exam(
        title="API测试考试",
        duration_minutes=30,
        status="published",
        created_by=hr_user.id,
    )
    session.add(exam)
    session.commit()
    session.refresh(exam)

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
        session.add(q)
        questions.append(q)
    session.commit()
    for q in questions:
        session.refresh(q)

    return hr_user, exam, questions


def _hr_token(user_id: int) -> str:
    return create_access_token(subject=user_id)


class TestCreateExamRecord:
    def test_create_success(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        resp = c.post(
            "/api/v1/exam-records",
            json={
                "exam_id": exam.id,
                "candidate_name": "张三",
                "candidate_phone": "13800138000",
                "candidate_email": "zhangsan@test.com",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["candidate_name"] == "张三"
        assert data["data"]["status"] == "not_started"
        assert data["data"]["exam_id"] == exam.id

    def test_create_minimal(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        resp = c.post(
            "/api/v1/exam-records",
            json={
                "exam_id": exam.id,
                "candidate_name": "李四",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["candidate_phone"] is None
        assert data["data"]["candidate_email"] is None

    def test_create_exam_not_found(self, client):
        c, _ = client

        resp = c.post(
            "/api/v1/exam-records",
            json={
                "exam_id": 999,
                "candidate_name": "张三",
            },
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == 404

    def test_create_empty_name(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        resp = c.post(
            "/api/v1/exam-records",
            json={
                "exam_id": exam.id,
                "candidate_name": "",
            },
        )
        assert resp.status_code == 422


class TestGetExamRecord:
    def test_get_success(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]

        resp = c.get(f"/api/v1/exam-records/{record_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["id"] == record_id

    def test_get_not_found(self, client):
        c, _ = client
        resp = c.get("/api/v1/exam-records/999")
        assert resp.status_code == 404


class TestStartExam:
    def test_start_success(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]

        resp = c.post(f"/api/v1/exam-records/{record_id}/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "in_progress"
        assert data["data"]["started_at"] is not None

    def test_start_already_started(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]

        c.post(f"/api/v1/exam-records/{record_id}/start")
        resp = c.post(f"/api/v1/exam-records/{record_id}/start")
        assert resp.status_code == 400


class TestSaveAnswer:
    def test_save_answer_success(self, client, setup_data):
        c, _ = client
        _, exam, questions = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers",
            json={"question_id": questions[0].id, "answer_content": "A"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["question_id"] == questions[0].id
        assert data["data"]["answer_content"] == "A"

    def test_save_answer_idempotent(self, client, setup_data):
        c, _ = client
        _, exam, questions = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        c.post(
            f"/api/v1/exam-records/{record_id}/answers",
            json={"question_id": questions[0].id, "answer_content": "A"},
        )
        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers",
            json={"question_id": questions[0].id, "answer_content": "B"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["answer_content"] == "B"

    def test_save_answer_after_submit(self, client, setup_data):
        c, _ = client
        _, exam, questions = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")
        c.post(f"/api/v1/exam-records/{record_id}/submit")

        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers",
            json={"question_id": questions[0].id, "answer_content": "A"},
        )
        assert resp.status_code == 400

    def test_save_answer_wrong_question(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers",
            json={"question_id": 999, "answer_content": "A"},
        )
        assert resp.status_code == 404


class TestSaveAnswersBatch:
    def test_batch_save_success(self, client, setup_data):
        c, _ = client
        _, exam, questions = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        batch_data = {
            "answers": [
                {"question_id": questions[0].id, "answer_content": "A"},
                {"question_id": questions[1].id, "answer_content": "B"},
                {"question_id": questions[2].id, "answer_content": "C"},
            ]
        }
        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers/batch",
            json=batch_data,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 3

    def test_batch_save_empty(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        resp = c.post(
            f"/api/v1/exam-records/{record_id}/answers/batch",
            json={"answers": []},
        )
        assert resp.status_code == 422


class TestSubmitExam:
    def test_submit_success(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]
        c.post(f"/api/v1/exam-records/{record_id}/start")

        resp = c.post(f"/api/v1/exam-records/{record_id}/submit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "submitted"
        assert data["data"]["submitted_at"] is not None

    def test_submit_not_started(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        create_resp = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        record_id = create_resp.json()["data"]["id"]

        resp = c.post(f"/api/v1/exam-records/{record_id}/submit")
        assert resp.status_code == 400


class TestHRListExamRecords:
    def test_hr_list_success(self, client, setup_data):
        c, _ = client
        hr_user, exam, _ = setup_data
        token = _hr_token(hr_user.id)

        c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "李四"},
        )

        resp = c.get(
            f"/api/v1/exams/{exam.id}/records",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2

    def test_hr_list_unauthorized(self, client, setup_data):
        c, _ = client
        _, exam, _ = setup_data

        resp = c.get(f"/api/v1/exams/{exam.id}/records")
        assert resp.status_code == 401

    def test_hr_list_wrong_role(self, client, setup_data, db_session):
        c, _ = client
        _, exam, _ = setup_data
        session, _, _ = db_session

        normal_user = User(
            username="normal_user",
            password_hash=hash_password("testpass123"),
            display_name="Normal User",
            role="candidate",
            status="active",
        )
        session.add(normal_user)
        session.commit()
        session.refresh(normal_user)

        token = _hr_token(normal_user.id)
        resp = c.get(
            f"/api/v1/exams/{exam.id}/records",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_hr_list_with_status_filter(self, client, setup_data):
        c, _ = client
        hr_user, exam, _ = setup_data
        token = _hr_token(hr_user.id)

        r1 = c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "张三"},
        )
        c.post(f"/api/v1/exam-records/{r1.json()['data']['id']}/start")
        c.post(f"/api/v1/exam-records/{r1.json()['data']['id']}/submit")

        c.post(
            "/api/v1/exam-records",
            json={"exam_id": exam.id, "candidate_name": "李四"},
        )

        resp = c.get(
            f"/api/v1/exams/{exam.id}/records?status=submitted",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["candidate_name"] == "张三"
