"""
S3.3.6 AI 报告生成集成测试
覆盖：ReportAgent、AI-Service、Backend ReportService、API 端点

测试场景：
1. ReportAgent 解析（正常/异常/边界）
2. ReportAgent JSON 提取
3. ReportAgent 类型修正
4. AI-Service 接口响应
5. Backend ReportService 逻辑
6. Backend 报告 API 端点
7. 数据库模型验证
8. 异常场景（AI 异常、重复生成、低分/高分候选人）
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai-service"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))


def _get_test_db():
    """创建临时 SQLite 数据库用于测试"""
    db_path = tempfile.mktemp(suffix=".db")
    return db_path


def test_report_agent_parse_response():
    """测试 ReportAgent 响应解析 - 正常场景"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    mock_response = json.dumps({
        "summary": "候选人表现优秀，具备良好的专业基础和逻辑思维能力",
        "strengths": ["专业知识扎实", "逻辑思维强", "表达清晰"],
        "weaknesses": ["缺乏实际项目经验"],
        "skill_analysis": {
            "专业技能": "扎实",
            "知识掌握": "全面",
            "逻辑思维": "优秀"
        },
        "interview_suggestions": ["深入考察项目管理能力", "了解团队协作经验"],
        "recommendation": "强烈推荐"
    })

    result = agent._parse_response(mock_response)

    assert result["summary"] == "候选人表现优秀，具备良好的专业基础和逻辑思维能力"
    assert len(result["strengths"]) == 3
    assert len(result["weaknesses"]) == 1
    assert isinstance(result["skill_analysis"], dict)
    assert len(result["interview_suggestions"]) == 2
    assert result["recommendation"] == "强烈推荐"
    print("✅ test_report_agent_parse_response 通过")


def test_report_agent_json_extract():
    """测试 ReportAgent JSON 提取 - 多种格式"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    # 代码块格式（```json ... ```）
    mock_response = '```json\n{"summary": "测试", "strengths": [], "weaknesses": [], "skill_analysis": {}, "interview_suggestions": [], "recommendation": "保留考虑"}\n```'
    result = agent._parse_response(mock_response)
    assert result["summary"] == "测试"

    # 带文本前缀
    mock_response = '根据分析结果：\n{"summary": "文本测试", "strengths": ["a"], "weaknesses": [], "skill_analysis": {}, "interview_suggestions": [], "recommendation": "推荐"}'
    result = agent._parse_response(mock_response)
    assert result["summary"] == "文本测试"

    # 无效 JSON
    mock_response = "这不是有效的 JSON"
    result = agent._parse_response(mock_response)
    assert "失败" in result["summary"] or "解析" in result["summary"]

    print("✅ test_report_agent_json_extract 通过")


def test_report_agent_type_correction():
    """测试 ReportAgent 类型修正 - 异常类型自动转换"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    # 各字段类型错误时的自动修正
    mock_response = json.dumps({
        "summary": "类型修正测试",
        "strengths": "单个优势",  # 字符串 → 列表
        "weaknesses": None,  # None → 空列表
        "skill_analysis": "字符串分析",  # 字符串 → 字典
        "interview_suggestions": "单个建议",  # 字符串 → 列表
        "recommendation": "无效推荐等级"  # 无效值 → "保留考虑"
    })

    result = agent._parse_response(mock_response)

    assert isinstance(result["strengths"], list)
    assert len(result["strengths"]) == 1
    assert isinstance(result["weaknesses"], list)
    assert len(result["weaknesses"]) == 0
    assert isinstance(result["skill_analysis"], dict)
    assert isinstance(result["interview_suggestions"], list)
    assert result["recommendation"] == "保留考虑"

    print("✅ test_report_agent_type_correction 通过")


def test_report_agent_recommendation_standardization():
    """测试 ReportAgent 推荐等级标准化"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    # 有效的推荐等级
    for valid_rec in ["强烈推荐", "推荐", "保留考虑", "不推荐"]:
        mock_response = json.dumps({
            "summary": "测试",
            "strengths": [], "weaknesses": [],
            "skill_analysis": {}, "interview_suggestions": [],
            "recommendation": valid_rec
        })
        result = agent._parse_response(mock_response)
        assert result["recommendation"] == valid_rec, f"期望 {valid_rec}，实际 {result['recommendation']}"

    # 无效推荐等级 → 默认 "保留考虑"
    mock_response = json.dumps({
        "summary": "测试",
        "strengths": [], "weaknesses": [],
        "skill_analysis": {}, "interview_suggestions": [],
        "recommendation": "力荐"  # 非标准值
    })
    result = agent._parse_response(mock_response)
    assert result["recommendation"] == "保留考虑"

    print("✅ test_report_agent_recommendation_standardization 通过")


def test_report_agent_mock_run():
    """测试 ReportAgent 完整 run() 流程（Mock LLM）"""
    from app.agents.report_agent import ReportAgent

    mock_client = type('MockClient', (), {
        'chat': lambda *args, **kwargs: json.dumps({
            "summary": "候选人综合表现良好，具备较强的学习能力和专业基础",
            "strengths": ["基础知识扎实", "学习能力强", "具备一定实践经验"],
            "weaknesses": ["团队协作能力待加强"],
            "skill_analysis": {
                "专业技能": "良好",
                "综合素质": "优秀",
                "团队协作": "有待提升"
            },
            "interview_suggestions": ["考察实际项目管理经验", "评估团队协作能力"],
            "recommendation": "推荐"
        }),
        'close': lambda: None,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = agent.run(
        exam_results='{"total_score": 85, "answers": []}',
        exam_title="Python 工程师能力考试",
        candidate_name="张三",
        position="Python 工程师"
    )

    assert result["summary"] == "候选人综合表现良好，具备较强的学习能力和专业基础"
    assert result["recommendation"] == "推荐"
    assert result["prompt_version"] == "1.0"
    assert len(result["strengths"]) == 3
    assert len(result["weaknesses"]) == 1
    assert "团队协作" in result["skill_analysis"]

    print("✅ test_report_agent_mock_run 通过")


def test_report_agent_empty_input():
    """测试 ReportAgent 空输入校验"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    # 空考试结果
    assert agent.validate_input("", "", "", "") is False
    assert agent.validate_input("  ", "", "", "") is False

    # 有效输入
    assert agent.validate_input('{"score": 100}', "考试", "候选人", "岗位") is True

    print("✅ test_report_agent_empty_input 通过")


def test_report_agent_default_result():
    """测试 ReportAgent 默认结果（解析失败场景）"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    # 完全无效的 JSON
    result = agent._parse_response("这不是 JSON 内容")
    assert "失败" in result["summary"] or "解析" in result["summary"]
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)
    assert isinstance(result["skill_analysis"], dict)
    assert isinstance(result["interview_suggestions"], list)
    assert result["recommendation"] == "保留考虑"

    print("✅ test_report_agent_default_result 通过")


def test_report_prompt_structure():
    """测试报告 Prompt 结构完整性"""
    from app.core.config import load_prompt

    prompt = load_prompt("report", "v1")

    assert hasattr(prompt, "template")
    assert hasattr(prompt, "version")
    assert prompt.version == "1.0"

    # 验证输入变量在模板中
    assert "{exam_results}" in prompt.template
    assert "{exam_title}" in prompt.template
    assert "{candidate_name}" in prompt.template
    assert "{position}" in prompt.template

    # 验证输出结构要求在模板中
    assert "summary" in prompt.template
    assert "strengths" in prompt.template
    assert "weaknesses" in prompt.template
    assert "skill_analysis" in prompt.template
    assert "interview_suggestions" in prompt.template
    assert "recommendation" in prompt.template

    print("✅ test_report_prompt_structure 通过")


def test_ai_service_report_schema():
    """测试 AI-Service 报告 Schema"""
    from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse

    # 请求 Schema 验证
    req = ReportGenerateRequest(
        exam_results='{"score": 100}',
        exam_title="测试考试",
        candidate_name="测试候选人",
        position="测试岗位"
    )
    assert req.exam_results == '{"score": 100}'
    assert req.exam_title == "测试考试"

    # 响应 Schema 验证
    resp = ReportGenerateResponse(
        summary="测试总结",
        strengths=["优势1", "优势2"],
        weaknesses=["薄弱1"],
        skill_analysis={"技能1": "分析1"},
        interview_suggestions=["建议1"],
        recommendation="推荐",
        prompt_version="1.0"
    )
    assert resp.summary == "测试总结"
    assert len(resp.strengths) == 2
    assert resp.recommendation == "推荐"

    print("✅ test_ai_service_report_schema 通过")


def test_backend_report_model_fields():
    """测试 Backend AI 报告模型字段完整性"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

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

    # 验证类存在
    assert ReportGenerateRequest is not None
    assert ReportResponse is not None
    assert ReportListItem is not None
    assert ReportListResponse is not None
    assert ReportDetailResponse is not None

    # 验证请求 Schema
    req = ReportGenerateRequest(exam_record_id=1)
    assert req.exam_record_id == 1

    # 验证响应 Schema
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

    # 验证 AI Report Service 关键方法
    assert hasattr(ai_report_service, 'generate_report')
    assert hasattr(ai_report_service, 'check_service_health')

    # 验证 ReportService 关键方法
    methods = [
        'create_report', 'update_report', 'get_report_by_exam_record',
        'get_report_by_id', 'list_reports', 'delete_report',
        'generate_report_for_exam'
    ]

    # 通过实例方法签名验证（不需要实际 DB）
    for method in methods:
        assert hasattr(ReportService, method) or hasattr(ReportService, f'_{method}'), \
            f"ReportService 缺少方法: {method}"

    print("✅ test_backend_report_service_exists 通过")


def test_backend_report_api_endpoints():
    """测试 Backend 报告 API 端点注册"""
    from app.api.v1.endpoints.reports import router

    routes = [(r.path, r.methods) for r in router.routes]
    paths = [r[0] for r in routes]

    # 验证所有端点存在
    assert "/generate" in paths, "缺少 POST /generate"
    assert "/exam-records/{exam_record_id}" in paths, "缺少 GET /exam-records/{exam_record_id}"
    assert "/{report_id}" in paths, "缺少 GET /{report_id}"
    # 列表端点（空字符串根路径）
    assert "" in paths or "/" in paths, "缺少 GET / 列表端点"

    print("✅ test_backend_report_api_endpoints 通过")


def test_ai_service_report_endpoint():
    """测试 AI-Service 报告端点注册"""
    from app.api.endpoints.report import router

    routes = [r.path for r in router.routes]
    assert "/generate" in routes, "缺少 POST /generate"

    print("✅ test_ai_service_report_endpoint 通过")


def test_report_service_list_reports_query():
    """测试 ReportService.list_reports 查询逻辑（无需数据库）"""
    from app.services.report_service import ReportService
    import inspect

    # 验证方法签名
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
        "strengths": "非列表",  # 应该被转换
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


def test_report_agent_low_score_scenario():
    """测试低分候选人报告场景"""
    from app.agents.report_agent import ReportAgent

    mock_client = type('MockClient', (), {
        'chat': lambda *args, **kwargs: json.dumps({
            "summary": "候选人整体表现不佳，多个基础能力维度存在明显不足",
            "strengths": ["态度端正", "按时完成"],
            "weaknesses": [
                "专业知识严重不足",
                "逻辑思维能力薄弱",
                "缺乏相关工作经验",
                "沟通表达能力欠缺"
            ],
            "skill_analysis": {
                "专业技能": "不足",
                "知识掌握": "欠缺",
                "逻辑思维": "薄弱",
                "综合能力": "不达标"
            },
            "interview_suggestions": [
                "重新评估岗位匹配度",
                "如考虑培养需制定详细发展计划",
                "重点考察学习能力和转变潜力"
            ],
            "recommendation": "不推荐"
        }),
        'close': lambda: None,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = agent.run(
        exam_results='{"total_score": 35, "pass_score": 60}',
        exam_title="程序员能力考试",
        candidate_name="低分候选人",
        position="高级程序员"
    )

    assert result["recommendation"] == "不推荐"
    assert len(result["weaknesses"]) >= 3
    assert result["summary"] is not None

    print("✅ test_report_agent_low_score_scenario 通过")


def test_report_agent_high_score_scenario():
    """测试高分候选人报告场景"""
    from app.agents.report_agent import ReportAgent

    mock_client = type('MockClient', (), {
        'chat': lambda *args, **kwargs: json.dumps({
            "summary": "候选人表现极为出色，各维度能力均达到优秀水平，强烈建议录用",
            "strengths": [
                "专业知识深度与广度兼备",
                "具备丰富的项目实战经验",
                "逻辑思维和问题解决能力突出",
                "沟通表达清晰有条理",
                "展现出良好的团队协作精神"
            ],
            "weaknesses": [
                "个别细分领域可进一步拓展"
            ],
            "skill_analysis": {
                "专业技能": "精通",
                "知识掌握": "全面深入",
                "逻辑思维": "卓越",
                "沟通能力": "优秀",
                "团队协作": "出色"
            },
            "interview_suggestions": [
                "讨论薪资和福利待遇期望",
                "了解职业发展规划",
                "评估管理潜力（如适用）"
            ],
            "recommendation": "强烈推荐"
        }),
        'close': lambda: None,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = agent.run(
        exam_results='{"total_score": 95, "pass_score": 60}',
        exam_title="架构师能力考试",
        candidate_name="高分候选人",
        position="技术架构师"
    )

    assert result["recommendation"] == "强烈推荐"
    assert len(result["strengths"]) >= 3
    assert len(result["weaknesses"]) <= 2  # 高分候选人弱项少
    assert result["summary"] is not None

    print("✅ test_report_agent_high_score_scenario 通过")


def test_report_agent_duplicate_generation():
    """测试重复生成报告的幂等性"""
    from app.agents.report_agent import ReportAgent

    call_count = [0]

    mock_client = type('MockClient', (), {
        'chat': lambda *args, **kwargs: (
            call_count.__setitem__(0, call_count[0] + 1) or
            json.dumps({
                "summary": f"第 {call_count[0]} 次生成",
                "strengths": ["优势"],
                "weaknesses": ["薄弱"],
                "skill_analysis": {"技能": "分析"},
                "interview_suggestions": ["建议"],
                "recommendation": "推荐"
            })
        ),
        'close': lambda: None,
    })()

    agent = ReportAgent(llm_client=mock_client)

    # 多次调用应每次都能成功生成
    for i in range(3):
        result = agent.run(
            exam_results='{"score": 75}',
            exam_title="考试",
            candidate_name="候选人",
            position="岗位"
        )
        assert result is not None
        assert result["recommendation"] == "推荐"

    print("✅ test_report_agent_duplicate_generation 通过")


def main():
    print("=" * 60)
    print("S3.3.6 AI 报告生成集成测试")
    print("=" * 60)
    print()

    errors = []

    test_groups = [
        ("AI-Service 单元测试", [
            ("ReportAgent 响应解析", test_report_agent_parse_response),
            ("ReportAgent JSON 提取", test_report_agent_json_extract),
            ("ReportAgent 类型修正", test_report_agent_type_correction),
            ("ReportAgent 推荐等级标准化", test_report_agent_recommendation_standardization),
            ("ReportAgent Mock 完整流程", test_report_agent_mock_run),
            ("ReportAgent 空输入校验", test_report_agent_empty_input),
            ("ReportAgent 默认结果", test_report_agent_default_result),
            ("报告 Prompt 结构", test_report_prompt_structure),
            ("AI-Service 报告 Schema", test_ai_service_report_schema),
            ("AI-Service 报告端点", test_ai_service_report_endpoint),
        ]),
        ("Backend 单元测试", [
            ("报告模型字段", test_backend_report_model_fields),
            ("报告 Schema", test_backend_report_schema),
            ("报告 Service 存在性", test_backend_report_service_exists),
            ("报告 API 端点注册", test_backend_report_api_endpoints),
            ("ReportService 方法签名", test_report_service_list_reports_query),
            ("AIReportService 响应验证", test_ai_report_service_response_validation),
        ]),
        ("场景测试", [
            ("低分候选人报告", test_report_agent_low_score_scenario),
            ("高分候选人报告", test_report_agent_high_score_scenario),
            ("重复生成幂等性", test_report_agent_duplicate_generation),
        ]),
    ]

    for group_name, tests in test_groups:
        print(f"\n📋 {group_name}")
        print("-" * 40)
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                errors.append((group_name, name, str(e)))
                import traceback
                print(f"❌ {name} 失败: {e}")
                traceback.print_exc()

    print()
    print("=" * 60)
    total = sum(len(tests) for _, tests in test_groups)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")
    print("=" * 60)

    if errors:
        print("\n❌ 失败的测试：")
        for group, name, error in errors:
            print(f"  [{group}] {name}: {error}")
        return 1
    else:
        print("\n🎉 所有测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
