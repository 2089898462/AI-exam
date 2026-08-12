"""
S3.3.4 AI-Service 调用链路测试
测试 Backend → AI-Service 调用链路

测试用例：
1. AI-Service Prompt 加载
2. AI-Service Scoring Agent 正常评分
3. AI-Service Scoring Agent 响应解析
4. Backend AI 评分 Service 调用（正常）
5. Backend AI 评分 Service 调用（异常处理）
6. Backend AI 评分 Service 响应验证
"""
import json
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# AI-Service 端测试
# ============================================================

def test_prompt_loading():
    """测试 Prompt 模板加载"""
    from app.core.config import load_prompt

    prompt = load_prompt("scoring", "v1")

    assert prompt.version == "1.0", f"期望版本 1.0，实际 {prompt.version}"
    assert prompt.template, "Prompt 模板不能为空"
    assert "{question}" in prompt.template, "模板应包含 {question}"
    assert "{user_answer}" in prompt.template, "模板应包含 {user_answer}"
    assert "{standard_answer}" in prompt.template, "模板应包含 {standard_answer}"

    print("✅ test_prompt_loading 通过")


def test_prompt_rendering():
    """测试 Prompt 模板渲染"""
    from app.core.config import load_prompt, render_prompt

    prompt = load_prompt("scoring", "v1")
    rendered = render_prompt(
        prompt,
        question="什么是Python？",
        standard_answer="Python是一种编程语言",
        scoring_rules="回答要准确",
        user_answer="Python是一种高级编程语言",
    )

    assert "什么是Python？" in rendered
    assert "Python是一种编程语言" in rendered
    assert "回答要准确" in rendered
    assert "Python是一种高级编程语言" in rendered

    print("✅ test_prompt_rendering 通过")


def test_prompt_rendering_missing_var():
    """测试 Prompt 模板渲染 - 缺少变量"""
    from app.core.config import load_prompt, render_prompt

    prompt = load_prompt("scoring", "v1")

    try:
        render_prompt(prompt, question="测试")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "模板变量缺失" in str(e)

    print("✅ test_prompt_rendering_missing_var 通过")


def test_scoring_agent_response_parsing():
    """测试 ScoringAgent 响应解析"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    # 标准 JSON 响应
    raw = '{"score": 8.5, "reason": "回答较好", "missing_points": ["缺少示例"], "confidence": 0.9}'
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 8.5
    assert result["reason"] == "回答较好"
    assert result["missing_points"] == ["缺少示例"]
    assert result["confidence"] == 0.9

    # 带代码块的响应
    raw = '```json\n{"score": 5.0, "reason": "部分正确", "missing_points": [], "confidence": 0.7}\n```'
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 5.0
    assert result["reason"] == "部分正确"

    # 带额外文本的响应
    raw = '根据评分结果：\n{"score": 3.0, "reason": "回答不完整", "missing_points": ["关键点1", "关键点2"], "confidence": 0.5}\n评分完成。'
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 3.0
    assert len(result["missing_points"]) == 2

    # 无效 JSON 响应
    raw = "这不是 JSON 格式的回复"
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 0.0
    assert result["confidence"] == 0.0
    assert "格式错误" in result["reason"]

    # 分数范围限制（超出满分）
    raw = '{"score": 15.0, "reason": "完美", "missing_points": [], "confidence": 1.5}'
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 10.0  # 限制在满分
    assert result["confidence"] == 1.0  # 限制在 0-1

    # 负分数限制
    raw = '{"score": -5.0, "reason": "不好", "missing_points": [], "confidence": -0.1}'
    result = agent._parse_response(raw, max_score=10.0)

    assert result["score"] == 0.0  # 限制为 0
    assert result["confidence"] == 0.0  # 限制为 0

    print("✅ test_scoring_agent_response_parsing 通过")


def test_scoring_agent_input_validation():
    """测试 ScoringAgent 输入校验"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    # 正常输入
    assert agent.validate_input("题目", "答案", "用户答案", 10.0) == True

    # 空题目
    assert agent.validate_input("", "答案", "用户答案", 10.0) == False

    # 空用户答案
    assert agent.validate_input("题目", "答案", "", 10.0) == False

    # 空格答案
    assert agent.validate_input("题目", "答案", "   ", 10.0) == False

    # 满分 <= 0
    assert agent.validate_input("题目", "答案", "用户答案", 0.0) == False

    print("✅ test_scoring_agent_input_validation 通过")


def test_scoring_agent_run_with_mock():
    """测试 ScoringAgent.run() 使用 Mock LLM"""
    from app.agents.scoring_agent import ScoringAgent
    from app.llm.client import LLMClient

    # 创建 Mock LLM 客户端
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.chat.return_value = '{"score": 9.0, "reason": "回答优秀", "missing_points": [], "confidence": 0.95}'

    agent = ScoringAgent(llm_client=mock_client)

    # 运行评分
    import asyncio
    result = asyncio.run(agent.run(
        question="Python 是什么？",
        standard_answer="Python 是一种高级编程语言",
        user_answer="Python 是一种高级、解释型、通用的编程语言",
        max_score=10.0,
    ))

    assert result["score"] == 9.0
    assert result["reason"] == "回答优秀"
    assert result["confidence"] == 0.95

    # 验证 LLM 调用
    mock_client.chat.assert_called_once()
    call_args = mock_client.chat.call_args
    messages = call_args[0][0]
    assert len(messages) == 2  # system + user
    assert messages[0]["role"] == "system"
    assert "Python 是什么？" in messages[1]["content"]

    print("✅ test_scoring_agent_run_with_mock 通过")


# ============================================================
# Backend 端测试
# ============================================================

def test_ai_scoring_service_normal_call():
    """测试 Backend AI 评分 Service 正常调用"""
    import httpx
    from unittest.mock import patch

    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.post 返回正常响应
    mock_response = httpx.Response(
        200,
        json={
            "score": 8.5,
            "reason": "回答较好，覆盖了主要要点",
            "missing_points": ["缺少具体示例"],
            "confidence": 0.88,
        },
    )

    with patch("httpx.post", return_value=mock_response) as mock_post:
        result = service.evaluate_scoring(
            question="Python 是什么？",
            standard_answer="Python 是一种高级编程语言",
            user_answer="Python 是一种高级、解释型编程语言",
            max_score=10.0,
        )

        assert result["score"] == 8.5
        assert result["reason"] == "回答较好，覆盖了主要要点"
        assert result["confidence"] == 0.88
        assert len(result["missing_points"]) == 1

        # 验证请求参数
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["question"] == "Python 是什么？"
        assert request_data["max_score"] == 10.0

    print("✅ test_ai_scoring_service_normal_call 通过")


def test_ai_scoring_service_timeout():
    """测试 Backend AI 评分 Service 超时"""
    import httpx
    from unittest.mock import patch

    from app.exceptions import BusinessException
    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.post 抛出超时异常
    mock_request = httpx.Request("POST", "http://test")
    with patch("httpx.post", side_effect=httpx.TimeoutException("超时")):
        try:
            service.evaluate_scoring(
                question="测试题目",
                user_answer="测试答案",
            )
            assert False, "应该抛出 BusinessException"
        except BusinessException as e:
            assert "超时" in str(e)
            assert "TIMEOUT" in e.error_code

    print("✅ test_ai_scoring_service_timeout 通过")


def test_ai_scoring_service_connection_error():
    """测试 Backend AI 评分 Service 服务不可用"""
    import httpx
    from unittest.mock import patch

    from app.exceptions import BusinessException
    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.post 抛出连接异常
    with patch("httpx.post", side_effect=httpx.ConnectError("连接失败")):
        try:
            service.evaluate_scoring(
                question="测试题目",
                user_answer="测试答案",
            )
            assert False, "应该抛出 BusinessException"
        except BusinessException as e:
            assert "不可用" in str(e)
            assert "UNAVAILABLE" in e.error_code

    print("✅ test_ai_scoring_service_connection_error 通过")


def test_ai_scoring_service_server_error():
    """测试 Backend AI 评分 Service 服务端错误"""
    import httpx
    from unittest.mock import patch

    from app.exceptions import BusinessException
    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.post 抛出 500 错误
    mock_request = httpx.Request("POST", "http://test")
    mock_response = httpx.Response(
        500,
        request=mock_request,
        json={"detail": "模型调用失败"},
    )
    mock_error = httpx.HTTPStatusError("服务端错误", request=mock_request, response=mock_response)

    with patch("httpx.post", side_effect=mock_error):
        try:
            service.evaluate_scoring(
                question="测试题目",
                user_answer="测试答案",
            )
            assert False, "应该抛出 BusinessException"
        except BusinessException as e:
            assert "内部错误" in str(e)
            assert "INTERNAL_ERROR" in e.error_code

    print("✅ test_ai_scoring_service_server_error 通过")


def test_ai_scoring_service_bad_request():
    """测试 Backend AI 评分 Service 请求参数错误"""
    import httpx
    from unittest.mock import patch

    from app.exceptions import BusinessException
    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.post 抛出 400 错误
    mock_request = httpx.Request("POST", "http://test")
    mock_response = httpx.Response(
        400,
        request=mock_request,
        json={"detail": "用户答案不能为空"},
    )
    mock_error = httpx.HTTPStatusError("请求错误", request=mock_request, response=mock_response)

    with patch("httpx.post", side_effect=mock_error):
        try:
            service.evaluate_scoring(
                question="测试题目",
                user_answer="测试答案",
            )
            assert False, "应该抛出 BusinessException"
        except BusinessException as e:
            assert "参数错误" in str(e)
            assert "BAD_REQUEST" in e.error_code

    print("✅ test_ai_scoring_service_bad_request 通过")


def test_ai_scoring_service_response_validation():
    """测试 Backend AI 评分 Service 响应验证"""
    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # 完整数据验证
    result = service._validate_response({
        "score": 8.5,
        "reason": "回答优秀",
        "missing_points": ["缺少示例"],
        "confidence": 0.9,
    })
    assert result["score"] == 8.5
    assert result["reason"] == "回答优秀"
    assert result["missing_points"] == ["缺少示例"]
    assert result["confidence"] == 0.9

    # 分数负数处理
    result = service._validate_response({
        "score": -5.0,
        "reason": "",
        "missing_points": [],
        "confidence": 1.5,
    })
    assert result["score"] == 0.0
    assert result["confidence"] == 1.0

    # 类型转换
    result = service._validate_response({
        "score": "9.5",
        "reason": 123,
        "missing_points": "不是列表",
        "confidence": "0.8",
    })
    assert result["score"] == 9.5
    assert result["reason"] == "123"
    assert result["missing_points"] == ["不是列表"]
    assert result["confidence"] == 0.8

    # 缺少字段
    try:
        service._validate_response({"score": 5.0})
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "缺少" in str(e)

    print("✅ test_ai_scoring_service_response_validation 通过")


def test_ai_scoring_service_health_check():
    """测试 Backend AI 评分 Service 健康检查"""
    import httpx
    from unittest.mock import patch

    from app.services.ai_scoring_service import AIScoringService

    service = AIScoringService()

    # Mock httpx.get 返回 200
    mock_response = httpx.Response(200, json={"status": "ok"})
    with patch("httpx.get", return_value=mock_response):
        result = service.check_service_health()
        assert result == True

    # Mock httpx.get 抛出异常
    with patch("httpx.get", side_effect=httpx.ConnectError("连接失败")):
        result = service.check_service_health()
        assert result == False

    print("✅ test_ai_scoring_service_health_check 通过")


def test_backend_schema_validation():
    """测试 Backend Schema 验证"""
    from app.schemas.ai_scoring import AIScoringRequest, AIScoringResponse

    # 正常请求
    req = AIScoringRequest(
        question="Python 是什么？",
        user_answer="编程语言",
        max_score=10.0,
    )
    assert req.question == "Python 是什么？"
    assert req.max_score == 10.0

    # 正常响应
    resp = AIScoringResponse(
        score=8.5,
        reason="回答较好",
        missing_points=["缺少示例"],
        confidence=0.9,
    )
    assert resp.score == 8.5
    assert resp.confidence == 0.9

    # 验证响应范围
    try:
        AIScoringResponse(score=10.0, reason="", missing_points=[], confidence=1.5)
        assert False, "confidence 超出范围应该失败"
    except Exception:
        pass

    print("✅ test_backend_schema_validation 通过")


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("S3.3.4 AI-Service 调用链路测试")
    print("=" * 60)
    print()

    errors = []

    ai_service_tests = [
        ("Prompt 加载", test_prompt_loading),
        ("Prompt 渲染", test_prompt_rendering),
        ("Prompt 渲染-缺变量", test_prompt_rendering_missing_var),
        ("Agent 响应解析", test_scoring_agent_response_parsing),
        ("Agent 输入校验", test_scoring_agent_input_validation),
        ("Agent 执行(Mock)", test_scoring_agent_run_with_mock),
    ]

    backend_tests = [
        ("Backend 正常调用", test_ai_scoring_service_normal_call),
        ("Backend 超时异常", test_ai_scoring_service_timeout),
        ("Backend 服务不可用", test_ai_scoring_service_connection_error),
        ("Backend 服务端错误", test_ai_scoring_service_server_error),
        ("Backend 请求错误", test_ai_scoring_service_bad_request),
        ("Backend 响应验证", test_ai_scoring_service_response_validation),
        ("Backend 健康检查", test_ai_scoring_service_health_check),
        ("Backend Schema 验证", test_backend_schema_validation),
    ]

    print("📋 AI-Service 端测试")
    print("-" * 40)
    for name, test_func in ai_service_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()
    print("📋 Backend 端测试")
    print("-" * 40)
    for name, test_func in backend_tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()
    print("=" * 60)
    total = len(ai_service_tests) + len(backend_tests)
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
