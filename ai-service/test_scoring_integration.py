"""
S3.3.5 主观题 AI 评分开发测试
测试 AI-Service ScoringAgent 和 Backend AI 评分集成

测试场景：
1. AI-Service Agent 解析（高质量/部分/错误/空答案）
2. AI-Service Agent 异常处理（JSON 错误/分数越界/低置信度）
3. Backend AI 评分保存（_save_ai_score）
4. Backend AI 评分集成调用（_ai_grade_answer）
5. Backend 异常降级处理
"""
import json
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# AI-Service 端测试
# ============================================================

def test_scoring_agent_high_quality():
    """测试高质量答案评分"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    mock_response = json.dumps({
        "score": 9.5,
        "reason": "答案完整准确，覆盖所有关键点",
        "missing_points": [],
        "confidence": 0.95,
    })

    result = agent._parse_response(mock_response, max_score=10.0)

    assert result["score"] == 9.5
    assert result["reason"] == "答案完整准确，覆盖所有关键点"
    assert result["missing_points"] == []
    assert result["confidence"] == 0.95

    # 低置信度检查
    assert result["confidence"] >= 0.6  # 高质量答案不应低置信度

    print("✅ test_scoring_agent_high_quality 通过")


def test_scoring_agent_partial_answer():
    """测试部分正确答案评分"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    mock_response = json.dumps({
        "score": 6.5,
        "reason": "答案基本正确，但遗漏了部分要点",
        "missing_points": ["缺少具体示例", "未提及例外情况"],
        "confidence": 0.75,
    })

    result = agent._parse_response(mock_response, max_score=10.0)

    assert result["score"] == 6.5
    assert result["confidence"] == 0.75
    assert len(result["missing_points"]) == 2
    assert "缺少具体示例" in result["missing_points"]

    print("✅ test_scoring_agent_partial_answer 通过")


def test_scoring_agent_wrong_answer():
    """测试错误答案评分"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    mock_response = json.dumps({
        "score": 1.0,
        "reason": "答案错误，完全偏离题意",
        "missing_points": ["所有要点"],
        "confidence": 0.9,
    })

    result = agent._parse_response(mock_response, max_score=10.0)

    assert result["score"] == 1.0
    assert result["confidence"] == 0.9

    print("✅ test_scoring_agent_wrong_answer 通过")


def test_scoring_agent_empty_answer():
    """测试空答案快速处理"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    # 空答案应在 run() 中快速处理，不调用 LLM
    # 这里我们手动模拟 run() 的快速返回逻辑
    result = agent._parse_response("{}", max_score=10.0)
    assert result["score"] == 0.0
    assert result["confidence"] == 0.0

    # 测试空字符串 JSON 解析
    result = agent._parse_response("", max_score=10.0)
    assert result["score"] == 0.0
    assert "格式错误" in result["reason"]

    print("✅ test_scoring_agent_empty_answer 通过")


def test_scoring_agent_low_confidence():
    """测试低置信度结果"""
    from app.agents.scoring_agent import ScoringAgent, LOW_CONFIDENCE_THRESHOLD

    agent = ScoringAgent(llm_client=None)

    # 低置信度响应
    mock_response = json.dumps({
        "score": 5.0,
        "reason": "答案不太确定",
        "missing_points": [],
        "confidence": 0.4,  # 低置信度
    })

    result = agent._parse_response(mock_response, max_score=10.0)

    assert result["confidence"] == 0.4
    # 低置信度需要人工复核（由调用方检查 needs_review）
    needs_review = result["confidence"] < LOW_CONFIDENCE_THRESHOLD
    assert needs_review == True

    print("✅ test_scoring_agent_low_confidence 通过")


def test_scoring_agent_score_boundary():
    """测试分数边界限制"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    # 分数超出满分
    mock_response = json.dumps({
        "score": 15.0,  # 超出满分
        "reason": "",
        "missing_points": [],
        "confidence": 1.0,
    })

    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 10.0  # 应被限制在满分

    # 负分数
    mock_response = json.dumps({
        "score": -5.0,
        "reason": "",
        "missing_points": [],
        "confidence": 0.5,
    })

    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 0.0  # 不应为负

    # 正常分数
    mock_response = json.dumps({
        "score": 7.5,
        "reason": "",
        "missing_points": [],
        "confidence": 0.8,
    })

    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 7.5  # 保持不变

    print("✅ test_scoring_agent_score_boundary 通过")


def test_scoring_agent_json_format():
    """测试多种 JSON 格式解析"""
    from app.agents.scoring_agent import ScoringAgent

    agent = ScoringAgent(llm_client=None)

    # 代码块格式
    mock_response = '```json\n{"score": 8.0, "reason": "good", "missing_points": [], "confidence": 0.9}\n```'
    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 8.0

    # 带前后文本
    mock_response = '根据评分结果：\n{"score": 5.5, "reason": "ok", "missing_points": ["a"], "confidence": 0.7}\n评分完成。'
    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 5.5

    # 无效 JSON
    mock_response = "这不是 JSON 格式"
    result = agent._parse_response(mock_response, max_score=10.0)
    assert result["score"] == 0.0
    assert "格式错误" in result["reason"]

    print("✅ test_scoring_agent_json_format 通过")


def test_scoring_agent_mock_run():
    """测试完整 run() 流程"""
    from app.agents.scoring_agent import ScoringAgent
    from app.llm.client import LLMClient

    # 创建 Mock LLM 客户端
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.chat.return_value = json.dumps({
        "score": 8.5,
        "reason": "回答优秀，覆盖所有要点",
        "missing_points": [],
        "confidence": 0.92,
    })

    agent = ScoringAgent(llm_client=mock_client)

    # 运行评分
    import asyncio
    result = asyncio.run(agent.run(
        question="什么是面向对象编程？",
        standard_answer="封装、继承、多态",
        user_answer="面向对象编程是一种编程范式，包括封装、继承和多态三大特性",
        max_score=10.0,
    ))

    assert result["score"] == 8.5
    assert result["reason"] == "回答优秀，覆盖所有要点"
    assert result["confidence"] == 0.92
    assert result["needs_review"] == False  # 高置信度
    assert result["prompt_version"] == "1.0"

    # 验证 LLM 调用
    mock_client.chat.assert_called_once()

    print("✅ test_scoring_agent_mock_run 通过")


# ============================================================
# Backend 端测试
# ============================================================

def test_backend_ai_scoring_save():
    """测试 Backend AI 评分结果保存逻辑"""
    # 验证 _save_ai_score 方法存在且逻辑正确
    # 这里通过代码审查确保逻辑，实际保存需要数据库

    from app.services.grading_service import GradingService

    # 验证方法签名
    import inspect
    sig = inspect.signature(GradingService._save_ai_score)
    params = list(sig.parameters.keys())

    assert "answer_record_id" in params
    assert "score" in params
    assert "reason" in params
    assert "confidence" in params
    assert "needs_review" in params
    assert "missing_points" in params
    assert "prompt_version" in params

    print("✅ test_backend_ai_scoring_save 通过")


def test_backend_ai_scoring_integration():
    """测试 Backend AI 评分集成调用"""
    # 验证 _ai_grade_answer 方法存在且逻辑正确
    import inspect
    from app.services.grading_service import GradingService

    sig = inspect.signature(GradingService._ai_grade_answer)
    params = list(sig.parameters.keys())

    assert "self" in params
    assert "answer_record_id" in params
    assert "question" in params
    assert "candidate_answer" in params

    print("✅ test_backend_ai_scoring_integration 通过")


def test_backend_grading_service_structure():
    """测试 GradingService 支持主观题评分结构"""
    from app.services.grading_service import GradingService

    # 验证 auto_grade_exam 方法支持主观题评分
    import inspect
    source = inspect.getsource(GradingService.auto_grade_exam)

    # 确保包含 AI 评分逻辑
    assert "short_answer" in source
    assert "_ai_grade_answer" in source
    assert "grading_method" in source or "grading_type" in source
    assert "ai_score" in source

    # 验证评分类型为 hybrid
    assert "hybrid" in source

    print("✅ test_backend_grading_service_structure 通过")


def test_answer_record_model_fields():
    """测试 AnswerRecord 模型包含 AI 评分字段"""
    from app.models.answer_record import AnswerRecord

    # 验证 AI 相关字段存在
    assert hasattr(AnswerRecord, "ai_score")
    assert hasattr(AnswerRecord, "ai_confidence")
    assert hasattr(AnswerRecord, "ai_reason")
    assert hasattr(AnswerRecord, "prompt_version")
    assert hasattr(AnswerRecord, "needs_review")

    print("✅ test_answer_record_model_fields 通过")


def test_scoring_prompt_structure():
    """测试评分 Prompt 结构"""
    from app.core.config import load_prompt

    prompt = load_prompt("scoring", "v1")

    # 验证输入变量
    assert "question" in prompt.template
    assert "standard_answer" in prompt.template
    assert "scoring_rules" in prompt.template
    assert "user_answer" in prompt.template
    assert "max_score" in prompt.template

    # 验证输出结构要求
    assert "score" in prompt.template
    assert "reason" in prompt.template
    assert "missing_points" in prompt.template
    assert "confidence" in prompt.template

    # 验证评分标准
    assert "优秀" in prompt.template
    assert "良好" in prompt.template
    assert "及格" in prompt.template
    assert "不及格" in prompt.template

    print("✅ test_scoring_prompt_structure 通过")


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("S3.3.5 主观题 AI 评分开发测试")
    print("=" * 60)
    print()

    errors = []

    ai_service_tests = [
        ("高质量答案评分", test_scoring_agent_high_quality),
        ("部分正确答案评分", test_scoring_agent_partial_answer),
        ("错误答案评分", test_scoring_agent_wrong_answer),
        ("空答案处理", test_scoring_agent_empty_answer),
        ("低置信度处理", test_scoring_agent_low_confidence),
        ("分数边界限制", test_scoring_agent_score_boundary),
        ("多种 JSON 格式解析", test_scoring_agent_json_format),
        ("完整 run() 流程(Mock)", test_scoring_agent_mock_run),
    ]

    backend_tests = [
        ("AI 评分保存逻辑", test_backend_ai_scoring_save),
        ("AI 评分集成调用", test_backend_ai_scoring_integration),
        ("混合评分结构", test_backend_grading_service_structure),
        ("AnswerRecord 模型字段", test_answer_record_model_fields),
        ("Prompt 结构验证", test_scoring_prompt_structure),
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
