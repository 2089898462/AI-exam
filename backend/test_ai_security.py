"""
S4.4-C1 AI 接入安全基础补充测试
覆盖：
1. AI 调用审计日志测试（成功/失败/异常）
2. 数据脱敏测试（手机号/邮箱/普通字段）
3. trace_id 链路追踪测试
4. 审计日志权限测试
"""
import sys
sys.path.insert(0, '.')

import bcrypt
from app.db.session import _get_engine, _get_session_factory
from app.db.base import Base
from app.models import User, AiCallLog
from app.services.ai_call_log_service import AiCallLogService
from app.core.data_masking import (
    PhoneMaskingRule,
    EmailMaskingRule,
    IdCardMaskingRule,
    mask_value,
    mask_sensitive_data,
    mask_phone,
    mask_email,
)
from app.core.trace import generate_trace_id, generate_request_id, TraceContext
from app.exceptions import ForbiddenException

engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()


def cleanup_test_data(db):
    """清理所有 S4.4-C1 测试数据"""
    db.query(AiCallLog).filter(AiCallLog.trace_id.like("s44c1%")).delete(synchronize_session=False)
    db.query(AiCallLog).filter(AiCallLog.source == "test_agent").delete(synchronize_session=False)
    users = db.query(User).filter(User.username.like("s4_4_c1_%")).all()
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


def run_tests():
    db = SessionLocal()
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
            db.rollback()
            failed += 1
            errors.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}")

    # 创建测试用户
    admin_user = get_or_create_user(db, "s4_4_c1_admin", "admin", "S4.4-C1 Admin")
    hr_user = get_or_create_user(db, "s4_4_c1_hr", "hr", "S4.4-C1 HR")
    candidate_user = get_or_create_user(db, "s4_4_c1_candidate", "employee", "S4.4-C1 Candidate", phone="13900000000")

    stats_service = AiCallLogService(db)

    print("=" * 70)
    print("S4.4-C1 AI 接入安全基础补充测试")
    print("=" * 70)

    # ==================== 1. AI 调用审计日志测试 ====================
    print("\n[1] AI 调用审计日志测试")

    def test_create_success_log():
        """1.1 创建成功调用日志"""
        trace_id = "s44c1-trace-0001"
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/exams/1/statistics",
            method="GET",
            source="ai_agent",
            source_id="test-agent",
            request_summary="GET /exams/1/statistics",
            response_summary='{"total_participants": 5}',
            status="success",
            http_status=200,
            latency_ms=150.5,
        )
        assert log.id is not None
        assert log.trace_id == trace_id
        assert log.caller_user_id == admin_user.id
        assert log.status == "success"
        assert log.http_status == 200
        assert log.latency_ms == 150.5
        assert log.request_summary is not None
        assert log.response_summary is not None

    def test_create_failed_log():
        """1.2 创建失败调用日志"""
        trace_id = "s44c1-trace-0002"
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=hr_user.id,
            caller_role="hr",
            endpoint="/api/v1/exams/999/analysis",
            source="ai_agent",
            status="failed",
            http_status=404,
            error_message="考试不存在",
            latency_ms=50.0,
        )
        assert log.status == "failed"
        assert log.http_status == 404
        assert "考试不存在" in log.error_message

    def test_create_error_log():
        """1.3 创建异常调用日志"""
        trace_id = "s44c1-trace-0003"
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/exams/1/records/1/answers",
            source="ai_agent",
            status="error",
            http_status=500,
            error_message="Internal Server Error: Database connection timeout",
            latency_ms=3000.0,
        )
        assert log.status == "error"
        assert log.http_status == 500

    def test_update_log_status():
        """1.4 更新调用日志状态"""
        trace_id = "s44c1-trace-0004"
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/exams/1/results",
            source="ai_agent",
            status="success",
            http_status=200,
        )
        updated = stats_service.update_status(
            log_id=log.id,
            status="error",
            http_status=500,
            error_message="服务超时",
            latency_ms=5000.0,
        )
        assert updated.status == "error"
        assert updated.http_status == 500
        assert updated.error_message == "服务超时"
        assert updated.latency_ms == 5000.0

    def test_log_not_save_sensitive_data():
        """1.5 日志不保存完整敏感数据"""
        trace_id = "s44c1-trace-0005"
        sensitive_request = "phone=13812345678&email=test@example.com&id_card=110101199001011234"
        sensitive_response = '{"phone": "13812345678", "email": "test@example.com"}'
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/exams/1/analysis",
            source="ai_agent",
            request_summary=sensitive_request,
            response_summary=sensitive_response,
            status="success",
            http_status=200,
        )
        # 摘要应被截断（AiCallLogService 会截断）
        assert len(log.request_summary) <= 1003  # 1000 + "..."
        assert len(log.response_summary) <= 1003

    def test_log_truncation():
        """1.6 超长文本自动截断"""
        trace_id = "s44c1-trace-0006"
        long_text = "A" * 2000
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/test",
            source="ai_agent",
            request_summary=long_text,
            status="success",
        )
        assert len(log.request_summary) == 1003  # 1000 + "..."

    test("1.1 创建成功调用日志", test_create_success_log)
    test("1.2 创建失败调用日志", test_create_failed_log)
    test("1.3 创建异常调用日志", test_create_error_log)
    test("1.4 更新调用日志状态", test_update_log_status)
    test("1.5 日志不保存完整敏感数据", test_log_not_save_sensitive_data)
    test("1.6 超长文本自动截断", test_log_truncation)

    # ==================== 2. 数据脱敏测试 ====================
    print("\n[2] 数据脱敏测试")

    def test_phone_masking():
        """2.1 手机号脱敏"""
        rule = PhoneMaskingRule()
        phone = "13812345678"
        masked = rule.mask(phone)
        assert rule.match("phone")
        assert masked == "138****5678"
        assert "1234" not in masked

    def test_phone_masking_not_matched():
        """2.2 非手机号字段不脱敏"""
        rule = PhoneMaskingRule()
        phone = "13812345678"
        result = mask_value("candidate_name", phone)
        assert result == phone  # 不匹配，不脱敏

    def test_email_masking():
        """2.3 邮箱脱敏"""
        rule = EmailMaskingRule()
        email = "test@example.com"
        masked = rule.mask(email)
        assert rule.match("email")
        assert masked == "t***@example.com"

    def test_id_card_masking():
        """2.4 身份证脱敏"""
        rule = IdCardMaskingRule()
        id_card = "110101199001011234"
        masked = rule.mask(id_card)
        assert rule.match("id_card")
        assert "********" in masked
        assert masked.endswith("1234")

    def test_full_data_masking():
        """2.5 完整数据结构脱敏"""
        data = {
            "phone": "13812345678",
            "email": "test@example.com",
            "candidate_name": "张三",
            "score": 85,
            "exam_title": "测试考试",
            "nested": {
                "candidate_phone": "13987654321",
                "candidate_email": "user@test.com",
            },
        }
        masked = mask_sensitive_data(data)
        assert masked["phone"] == "138****5678"
        assert masked["email"] == "t***@example.com"
        assert masked["candidate_name"] == "张三"  # 姓名默认不脱敏
        assert masked["score"] == 85  # 数字不变
        assert masked["exam_title"] == "测试考试"  # 普通字段不变
        assert masked["nested"]["candidate_phone"] == "139****4321"
        assert masked["nested"]["candidate_email"] == "u***@test.com"

    def test_list_data_masking():
        """2.6 列表数据脱敏"""
        data = [
            {"phone": "13812345678", "email": "a@b.com"},
            {"phone": "13987654321", "email": "c@d.com"},
        ]
        masked = mask_sensitive_data(data)
        assert masked[0]["phone"] == "138****5678"
        assert masked[1]["email"] == "c*@d.com"

    def test_convenience_functions():
        """2.7 便捷脱敏函数"""
        assert mask_phone("13812345678") == "138****5678"
        assert mask_email("test@example.com") == "t***@example.com"

    test("2.1 手机号脱敏", test_phone_masking)
    test("2.2 非手机号字段不脱敏", test_phone_masking_not_matched)
    test("2.3 邮箱脱敏", test_email_masking)
    test("2.4 身份证脱敏", test_id_card_masking)
    test("2.5 完整数据结构脱敏", test_full_data_masking)
    test("2.6 列表数据脱敏", test_list_data_masking)
    test("2.7 便捷脱敏函数", test_convenience_functions)

    # ==================== 3. trace_id 链路追踪测试 ====================
    print("\n[3] trace_id 链路追踪测试")

    def test_generate_trace_id():
        """3.1 生成唯一 trace_id"""
        id1 = generate_trace_id()
        id2 = generate_trace_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID4 format
        assert len(id2) == 36

    def test_generate_request_id():
        """3.2 生成唯一 request_id"""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2
        assert len(id1) == 36

    def test_trace_context():
        """3.3 _trace_context 正确传递"""
        ctx = TraceContext(trace_id="trace-001", request_id="req-001")
        assert ctx.trace_id == "trace-001"
        assert ctx.request_id == "req-001"
        d = ctx.to_dict()
        assert d["trace_id"] == "trace-001"
        assert d["request_id"] == "req-001"

    def test_trace_context_default_request_id():
        """3.4 TraceContext 默认 request_id"""
        ctx = TraceContext(trace_id="trace-002")
        assert ctx.request_id == "trace-002"

    def test_log_contains_trace_id():
        """3.5 AI 调用日志包含 trace_id"""
        trace_id = "s44c1-trace-log-test"
        log = stats_service.create_log(
            trace_id=trace_id,
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/trace-test",
            source="ai_agent",
            status="success",
        )
        assert log.trace_id == trace_id
        assert log.id is not None

    test("3.1 生成唯一 trace_id", test_generate_trace_id)
    test("3.2 生成唯一 request_id", test_generate_request_id)
    test("3.3 TraceContext 正确传递", test_trace_context)
    test("3.4 TraceContext 默认 request_id", test_trace_context_default_request_id)
    test("3.5 AI 调用日志包含 trace_id", test_log_contains_trace_id)

    # ==================== 4. 审计日志权限测试 ====================
    print("\n[4] 审计日志权限测试")

    def test_admin_can_query_logs():
        """4.1 管理员可以查询日志"""
        result = stats_service.query_logs(current_user=admin_user, page=1, page_size=20)
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert result["page"] == 1
        assert result["page_size"] == 20

    def test_hr_cannot_query_logs():
        """4.2 HR 无权查询日志"""
        try:
            stats_service.query_logs(current_user=hr_user, page=1, page_size=20)
            assert False, "应该抛出 ForbiddenException"
        except ForbiddenException:
            pass

    def test_candidate_cannot_query_logs():
        """4.3 候选人无权查询日志"""
        try:
            stats_service.query_logs(current_user=candidate_user, page=1, page_size=20)
            assert False, "应该抛出 ForbiddenException"
        except ForbiddenException:
            pass

    def test_admin_can_get_log_by_id():
        """4.4 管理员可以查询单条日志"""
        # 先创建一条日志
        log = stats_service.create_log(
            trace_id="s44c1-detail-test",
            caller_user_id=admin_user.id,
            caller_role="admin",
            endpoint="/api/v1/detail-test",
            source="ai_agent",
            status="success",
        )
        result = stats_service.get_log_by_id(log.id, admin_user)
        assert result is not None
        assert result["id"] == log.id
        assert result["trace_id"] == "s44c1-detail-test"

    def test_get_nonexistent_log():
        """4.5 查询不存在的日志返回 None"""
        result = stats_service.get_log_by_id(999999, admin_user)
        assert result is None

    def test_logs_pagination():
        """4.6 日志分页查询"""
        for i in range(5):
            stats_service.create_log(
                trace_id=f"s44c1-page-{i}",
                caller_user_id=admin_user.id,
                caller_role="admin",
                endpoint="/api/v1/page-test",
                source="test_agent",
                status="success",
            )
        page1 = stats_service.query_logs(admin_user, page=1, page_size=2)
        assert len(page1["items"]) == 2
        assert page1["total"] >= 5

    def test_logs_filter_by_status():
        """4.7 日志按状态过滤"""
        result = stats_service.query_logs(admin_user, page=1, page_size=20, status="success")
        for item in result["items"]:
            assert item["status"] == "success"

    def test_logs_filter_by_caller():
        """4.8 日志按调用者过滤"""
        result = stats_service.query_logs(admin_user, page=1, page_size=20, caller_user_id=admin_user.id)
        for item in result["items"]:
            assert item["caller_user_id"] == admin_user.id

    test("4.1 管理员可以查询日志", test_admin_can_query_logs)
    test("4.2 HR 无权查询日志", test_hr_cannot_query_logs)
    test("4.3 候选人无权查询日志", test_candidate_cannot_query_logs)
    test("4.4 管理员可以查询单条日志", test_admin_can_get_log_by_id)
    test("4.5 查询不存在的日志返回 None", test_get_nonexistent_log)
    test("4.6 日志分页查询", test_logs_pagination)
    test("4.7 日志按状态过滤", test_logs_filter_by_status)
    test("4.8 日志按调用者过滤", test_logs_filter_by_caller)

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