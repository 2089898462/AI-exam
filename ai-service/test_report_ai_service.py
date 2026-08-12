"""
S3.3.6 AI 报告生成测试 - AI-Service 侧
覆盖：ReportAgent、Prompt、Schema、API 端点
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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

    # 代码块格式
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
    """测试 ReportAgent 类型修正"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

    mock_response = json.dumps({
        "summary": "类型修正测试",
        "strengths": "单个优势",
        "weaknesses": None,
        "skill_analysis": "字符串分析",
        "interview_suggestions": "单个建议",
        "recommendation": "无效推荐等级"
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
        "recommendation": "力荐"
    })
    result = agent._parse_response(mock_response)
    assert result["recommendation"] == "保留考虑"

    print("✅ test_report_agent_recommendation_standardization 通过")


def test_report_agent_mock_run():
    """测试 ReportAgent 完整 run() 流程（Mock LLM）"""
    import asyncio
    from app.agents.report_agent import ReportAgent

    async def mock_chat(*args, **kwargs):
        return json.dumps({
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
        })

    async def mock_close():
        return None

    mock_client = type('MockClient', (), {
        'chat': mock_chat,
        'close': mock_close,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = asyncio.run(agent.run(
        exam_results='{"total_score": 85, "answers": []}',
        exam_title="Python 工程师能力考试",
        candidate_name="张三",
        position="Python 工程师"
    ))

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

    assert agent.validate_input("", "", "", "") is False
    assert agent.validate_input("  ", "", "", "") is False
    assert agent.validate_input('{"score": 100}', "考试", "候选人", "岗位") is True

    print("✅ test_report_agent_empty_input 通过")


def test_report_agent_default_result():
    """测试 ReportAgent 默认结果（解析失败场景）"""
    from app.agents.report_agent import ReportAgent

    agent = ReportAgent(llm_client=None)

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

    assert "{exam_results}" in prompt.template
    assert "{exam_title}" in prompt.template
    assert "{candidate_name}" in prompt.template
    assert "{position}" in prompt.template

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

    req = ReportGenerateRequest(
        exam_results='{"score": 100}',
        exam_title="测试考试",
        candidate_name="测试候选人",
        position="测试岗位"
    )
    assert req.exam_results == '{"score": 100}'
    assert req.exam_title == "测试考试"

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


def test_ai_service_report_endpoint():
    """测试 AI-Service 报告端点注册"""
    from app.api.endpoints.report import router

    routes = [r.path for r in router.routes]
    assert "/generate" in routes

    print("✅ test_ai_service_report_endpoint 通过")


def test_report_agent_low_score_scenario():
    """测试低分候选人报告场景"""
    import asyncio
    from app.agents.report_agent import ReportAgent

    async def mock_chat_low(*args, **kwargs):
        return json.dumps({
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
        })

    async def mock_close():
        return None

    mock_client = type('MockClient', (), {
        'chat': mock_chat_low,
        'close': mock_close,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = asyncio.run(agent.run(
        exam_results='{"total_score": 35, "pass_score": 60}',
        exam_title="程序员能力考试",
        candidate_name="低分候选人",
        position="高级程序员"
    ))

    assert result["recommendation"] == "不推荐"
    assert len(result["weaknesses"]) >= 3
    assert result["summary"] is not None

    print("✅ test_report_agent_low_score_scenario 通过")


def test_report_agent_high_score_scenario():
    """测试高分候选人报告场景"""
    import asyncio
    from app.agents.report_agent import ReportAgent

    async def mock_chat_high(*args, **kwargs):
        return json.dumps({
            "summary": "候选人表现极为出色，各维度能力均达到优秀水平",
            "strengths": [
                "专业知识深度与广度兼备",
                "具备丰富的项目实战经验",
                "逻辑思维和问题解决能力突出",
                "沟通表达清晰有条理",
                "展现出良好的团队协作精神"
            ],
            "weaknesses": ["个别细分领域可进一步拓展"],
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
        })

    async def mock_close():
        return None

    mock_client = type('MockClient', (), {
        'chat': mock_chat_high,
        'close': mock_close,
    })()

    agent = ReportAgent(llm_client=mock_client)

    result = asyncio.run(agent.run(
        exam_results='{"total_score": 95, "pass_score": 60}',
        exam_title="架构师能力考试",
        candidate_name="高分候选人",
        position="技术架构师"
    ))

    assert result["recommendation"] == "强烈推荐"
    assert len(result["strengths"]) >= 3
    assert len(result["weaknesses"]) <= 2
    assert result["summary"] is not None

    print("✅ test_report_agent_high_score_scenario 通过")


def test_report_agent_duplicate_generation():
    """测试重复生成报告的幂等性"""
    import asyncio
    from app.agents.report_agent import ReportAgent

    call_count = [0]

    async def mock_chat_dup(*args, **kwargs):
        call_count[0] += 1
        return json.dumps({
            "summary": f"第 {call_count[0]} 次生成",
            "strengths": ["优势"],
            "weaknesses": ["薄弱"],
            "skill_analysis": {"技能": "分析"},
            "interview_suggestions": ["建议"],
            "recommendation": "推荐"
        })

    async def mock_close():
        return None

    mock_client = type('MockClient', (), {
        'chat': mock_chat_dup,
        'close': mock_close,
    })()

    agent = ReportAgent(llm_client=mock_client)

    for i in range(3):
        result = asyncio.run(agent.run(
            exam_results='{"score": 75}',
            exam_title="考试",
            candidate_name="候选人",
            position="岗位"
        ))
        assert result is not None
        assert result["recommendation"] == "推荐"

    print("✅ test_report_agent_duplicate_generation 通过")


def main():
    print("=" * 60)
    print("S3.3.6 AI 报告生成测试 - AI-Service 侧")
    print("=" * 60)

    ai_service_tests = [
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
        ("低分候选人报告", test_report_agent_low_score_scenario),
        ("高分候选人报告", test_report_agent_high_score_scenario),
        ("重复生成幂等性", test_report_agent_duplicate_generation),
    ]

    errors = []
    for name, test_func in ai_service_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            import traceback
            print(f"❌ {name} 失败: {e}")
            traceback.print_exc()

    print()
    total = len(ai_service_tests)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")

    if errors:
        print("\n❌ 失败的测试：")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return 1

    print("\n🎉 所有 AI-Service 测试通过！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
