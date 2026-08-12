"""
Mock 集成测试 - 测试 Backend → AI-Service 完整调用链路
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from unittest.mock import patch

from app.services.ai_scoring_service import AIScoringService
from app.exceptions import BusinessException


def test_normal_flow():
    """测试正常调用流程"""
    service = AIScoringService()

    mock_request = httpx.Request("POST", "http://test")
    mock_response = httpx.Response(
        200,
        request=mock_request,
        json={
            "score": 8.5,
            "reason": "回答较好",
            "missing_points": ["缺少示例"],
            "confidence": 0.88,
        },
    )

    with patch("httpx.post", return_value=mock_response) as mock_post:
        result = service.evaluate_scoring(
            question="Python 是什么？",
            standard_answer="Python 是高级语言",
            user_answer="Python 是高级、解释型语言",
            max_score=10.0,
        )

        assert result["score"] == 8.5
        assert result["reason"] == "回答较好"
        assert result["confidence"] == 0.88
        assert len(result["missing_points"]) == 1

        # 验证请求
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["question"] == "Python 是什么？"
        assert call_kwargs["json"]["max_score"] == 10.0

    print("✅ test_normal_flow 通过")


def test_timeout_flow():
    """测试超时处理"""
    service = AIScoringService()

    with patch("httpx.post", side_effect=httpx.TimeoutException("超时")):
        try:
            service.evaluate_scoring(question="Q", user_answer="A")
            assert False, "应该抛出异常"
        except BusinessException as e:
            assert "超时" in str(e)
            assert "TIMEOUT" in e.error_code

    print("✅ test_timeout_flow 通过")


def test_connection_error_flow():
    """测试服务不可用"""
    service = AIScoringService()

    with patch("httpx.post", side_effect=httpx.ConnectError("连接失败")):
        try:
            service.evaluate_scoring(question="Q", user_answer="A")
            assert False, "应该抛出异常"
        except BusinessException as e:
            assert "不可用" in str(e)
            assert "UNAVAILABLE" in e.error_code

    print("✅ test_connection_error_flow 通过")


def test_server_error_flow():
    """测试 500 错误"""
    service = AIScoringService()

    mock_request = httpx.Request("POST", "http://test")
    mock_response = httpx.Response(
        500,
        request=mock_request,
        json={"detail": "模型错误"},
    )
    mock_error = httpx.HTTPStatusError("Error", request=mock_request, response=mock_response)

    with patch("httpx.post", side_effect=mock_error):
        try:
            service.evaluate_scoring(question="Q", user_answer="A")
            assert False, "应该抛出异常"
        except BusinessException as e:
            assert "内部错误" in str(e)
            assert "INTERNAL_ERROR" in e.error_code

    print("✅ test_server_error_flow 通过")


def test_validation_flow():
    """测试返回格式校验"""
    service = AIScoringService()

    # 正常格式
    result = service._validate_response({
        "score": 9.0, "reason": "ok", "missing_points": [], "confidence": 0.95
    })
    assert result["score"] == 9.0

    # 分数范围
    result = service._validate_response({
        "score": 20.0, "reason": "", "missing_points": [], "confidence": 2.0
    })
    assert result["score"] == 20.0  # validate_response doesn't cap to max_score
    assert result["confidence"] == 1.0

    # 缺字段
    try:
        service._validate_response({"score": 5})
        assert False
    except ValueError:
        pass

    print("✅ test_validation_flow 通过")


if __name__ == "__main__":
    print("=" * 50)
    print("Backend → AI-Service Mock 集成测试")
    print("=" * 50)
    print()

    tests = [
        test_normal_flow,
        test_timeout_flow,
        test_connection_error_flow,
        test_server_error_flow,
        test_validation_flow,
    ]

    errors = []
    for test in tests:
        try:
            test()
        except Exception as e:
            errors.append((test.__name__, str(e)))
            print(f"❌ {test.__name__} 失败: {e}")

    print()
    total = len(tests)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")

    if errors:
        print("\n失败的测试：")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\n🎉 所有 Mock 集成测试通过！")
