"""
S3.3.6 AI 报告生成测试 - Backend 侧
覆盖：报告模型、Schema、Service、API 端点
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_backend_report_model_fields():
    """测试 Backend AI 报告模型字段完整性"""
    from app.models.ai_report import AiReport

    required_fields = [
        'id', 'exam_record_id', 'summary', 'strengths', 'weaknesses',
        'skill_analysis', 'interview_suggestions', 'recommendation',
        'model_used', 'prompt_version', 'status', 'raw_report',
        'created_at', 'updated_at'
    ]

    for field in required_fields:
        assert hasattr(AiReport, field), f"字段 {field} 不存在"

    print("✅ test_backend_report_model_fields 通过")


def test_backend_report_schema():
    """测试 Backend 报告 Schema"""
    from app.schemas.report import (
        ReportGenerateRequest,
        ReportResponse,
        ReportListItem,
        ReportListResponse,
        ReportDetailResponse
    )

    assert ReportGenerateRequest is not None
    assert ReportResponse is not None
    assert ReportListItem is not None
    assert ReportListResponse is not None
    assert ReportDetailResponse is not None

    req = ReportGenerateRequest(exam_record_id=1)
    assert req.exam_record_id == 1

    resp = ReportResponse(
        id=1, exam_record_id=1,
        summary="测试",
        strengths=["优势"],
        weaknesses=["薄弱"],
        skill_analysis={"技能": "分析"},
        interview_suggestions=["建议"],
        recommendation="推荐",
        model_used="qwen-plus",
        prompt_version="1.0",
        status="completed",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    assert resp.id == 1
    assert resp.recommendation == "推荐"

    print("✅ test_backend_report_schema 通过")


def test_backend_report_service_exists():
    """测试 Backend 报告 Service 存在且接口完整"""
    from app.services.report_service import ReportService
    from app.services.ai_report_service import ai_report_service

    assert ReportService is not None
    assert ai_report_service is not None

    assert hasattr(ai_report_service, 'generate_report')
    assert hasattr(ai_report_service, 'check_service_health')

    methods = [
        'create_report', 'update_report', 'get_report_by_exam_record',
        'get_report_by_id', 'list_reports', 'delete_report',
        'generate_report_for_exam'
    ]

    for method in methods:
        assert hasattr(ReportService, method) or hasattr(ReportService, f'_{method}'), \
            f"ReportService 缺少方法: {method}"

    print("✅ test_backend_report_service_exists 通过")


def test_backend_report_api_endpoints():
    """测试 Backend 报告 API 端点注册"""
    from app.api.v1.endpoints.reports import router

    routes = [(r.path, r.methods) for r in router.routes]
    paths = [r[0] for r in routes]

    assert "/generate" in paths, "缺少 POST /generate"
    assert "/exam-records/{exam_record_id}" in paths, "缺少 GET /exam-records/{exam_record_id}"
    assert "/{report_id}" in paths, "缺少 GET /{report_id}"
    assert "" in paths or "/" in paths, "缺少 GET / 列表端点"

    print("✅ test_backend_report_api_endpoints 通过")


def test_report_service_list_reports_query():
    """测试 ReportService.list_reports 方法签名"""
    from app.services.report_service import ReportService
    import inspect

    sig = inspect.signature(ReportService.list_reports)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'page' in params
    assert 'page_size' in params

    print("✅ test_report_service_list_reports_query 通过")


def test_ai_report_service_response_validation():
    """测试 AIReportService 响应验证逻辑"""
    from app.services.ai_report_service import AIReportService

    service = AIReportService()

    # 验证正常响应
    valid_data = {
        "summary": "测试总结",
        "strengths": ["优势1"],
        "weaknesses": ["薄弱1"],
        "skill_analysis": {"技能": "分析"},
        "interview_suggestions": ["建议1"],
        "recommendation": "推荐",
        "prompt_version": "1.0"
    }
    result = service._validate_response(valid_data)
    assert result["summary"] == "测试总结"
    assert result["recommendation"] == "推荐"

    # 验证字段缺失
    try:
        service._validate_response({"summary": "只有总结"})
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "缺少必要字段" in str(e)

    # 验证类型修正
    invalid_data = {
        "summary": "测试",
        "strengths": "非列表",
        "weaknesses": None,
        "skill_analysis": "非字典",
        "interview_suggestions": "非列表",
        "recommendation": "无效等级",
        "prompt_version": "1.0"
    }
    result = service._validate_response(invalid_data)
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)
    assert isinstance(result["skill_analysis"], dict)
    assert isinstance(result["interview_suggestions"], list)
    assert result["recommendation"] == "保留考虑"

    print("✅ test_ai_report_service_response_validation 通过")


def test_report_generate_endpoint_logic():
    """测试报告生成端点的请求/响应逻辑"""
    from app.api.v1.endpoints.reports import _report_to_response, _report_to_list_item

    # 创建 mock 对象
    class MockReport:
        id = 1
        exam_record_id = 100
        summary = "测试总结"
        strengths = '["优势1"]'
        weaknesses = '["薄弱1"]'
        skill_analysis = '{"技能": "分析"}'
        interview_suggestions = '["建议1"]'
        recommendation = "推荐"
        model_used = "qwen-plus"
        prompt_version = "1.0"
        status = "completed"
        created_at = None
        updated_at = None

    result = _report_to_response(MockReport())
    assert result["id"] == 1
    assert result["recommendation"] == "推荐"
    assert isinstance(result["strengths"], list)
    assert isinstance(result["skill_analysis"], dict)

    print("✅ test_report_generate_endpoint_logic 通过")


def test_grading_service_ai_score_saved():
    """测试评分服务 AI 分数保存"""
    from app.services.grading_service import GradingService
    import inspect

    sig = inspect.signature(GradingService._complete_auto_grading)
    params = list(sig.parameters.keys())
    assert 'ai_score' in params, "_complete_auto_grading 缺少 ai_score 参数"

    print("✅ test_grading_service_ai_score_saved 通过")


def main():
    print("=" * 60)
    print("S3.3.6 AI 报告生成测试 - Backend 侧")
    print("=" * 60)

    backend_tests = [
        ("报告模型字段", test_backend_report_model_fields),
        ("报告 Schema", test_backend_report_schema),
        ("报告 Service 存在性", test_backend_report_service_exists),
        ("报告 API 端点注册", test_backend_report_api_endpoints),
        ("ReportService 方法签名", test_report_service_list_reports_query),
        ("AIReportService 响应验证", test_ai_report_service_response_validation),
        ("报告端点响应转换", test_report_generate_endpoint_logic),
        ("评分服务 AI 分数保存", test_grading_service_ai_score_saved),
    ]

    errors = []
    for name, test_func in backend_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            import traceback
            print(f"❌ {name} 失败: {e}")
            traceback.print_exc()

    print()
    total = len(backend_tests)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")

    if errors:
        print("\n❌ 失败的测试：")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return 1

    print("\n🎉 所有 Backend 测试通过！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
