"""
Backend 端 AI 评分集成测试
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ai_scoring_service_exists():
    """测试 AI 评分服务存在"""
    from app.services.ai_scoring_service import ai_scoring_service

    assert ai_scoring_service is not None
    assert hasattr(ai_scoring_service, 'evaluate_scoring')
    print("✅ test_ai_scoring_service_exists 通过")


def test_ai_scoring_service_interface():
    """测试 AI 评分服务接口"""
    from app.services.ai_scoring_service import AIScoringService
    import inspect

    # 验证 evaluate_scoring 方法签名
    sig = inspect.signature(AIScoringService.evaluate_scoring)
    params = list(sig.parameters.keys())

    assert "question" in params
    assert "standard_answer" in params
    assert "user_answer" in params
    assert "max_score" in params
    assert "scoring_rules" in params

    print("✅ test_ai_scoring_service_interface 通过")


def test_grading_service_ai_grade_method():
    """测试 GradingService AI 评分方法"""
    from app.services.grading_service import GradingService
    import inspect

    # 验证 _ai_grade_answer 方法存在
    assert hasattr(GradingService, '_ai_grade_answer')

    # 验证方法签名
    sig = inspect.signature(GradingService._ai_grade_answer)
    params = list(sig.parameters.keys())
    assert "answer_record_id" in params
    assert "question" in params
    assert "candidate_answer" in params

    print("✅ test_grading_service_ai_grade_method 通过")


def test_grading_service_save_ai_score_method():
    """测试 GradingService 保存 AI 评分方法"""
    from app.services.grading_service import GradingService
    import inspect

    # 验证 _save_ai_score 方法存在
    assert hasattr(GradingService, '_save_ai_score')

    # 验证方法签名
    sig = inspect.signature(GradingService._save_ai_score)
    params = list(sig.parameters.keys())
    assert "answer_record_id" in params
    assert "score" in params
    assert "reason" in params
    assert "confidence" in params

    print("✅ test_grading_service_save_ai_score_method 通过")


def test_answer_record_model_has_ai_fields():
    """测试 AnswerRecord 模型包含 AI 评分字段"""
    from app.models.answer_record import AnswerRecord

    # 验证 AI 相关字段存在
    assert hasattr(AnswerRecord, "ai_score")
    assert hasattr(AnswerRecord, "ai_confidence")
    assert hasattr(AnswerRecord, "ai_reason")
    assert hasattr(AnswerRecord, "prompt_version")
    assert hasattr(AnswerRecord, "needs_review")

    print("✅ test_answer_record_model_has_ai_fields 通过")


def test_grading_service_auto_grade_supports_ai():
    """测试自动评分支持 AI 主观题"""
    from app.services.grading_service import GradingService
    import inspect

    source = inspect.getsource(GradingService.auto_grade_exam)

    # 验证包含主观题 AI 评分逻辑
    assert "short_answer" in source
    assert "_ai_grade_answer" in source
    assert "ai_score" in source
    assert "hybrid" in source  # 混合评分类型

    print("✅ test_grading_service_auto_grade_supports_ai 通过")


def test_grading_result_detail_includes_ai_info():
    """测试评分结果详情包含 AI 信息"""
    from app.services.grading_service import GradingService
    import inspect

    source = inspect.getsource(GradingService.get_grading_result_detail)

    # 验证返回结果包含 AI 评分详情字段
    assert "ai_score" in source
    assert "ai_reason" in source
    assert "ai_confidence" in source
    assert "needs_review" in source
    assert "prompt_version" in source
    assert "needs_review_count" in source

    print("✅ test_grading_result_detail_includes_ai_info 通过")


def test_ai_scoring_service_config():
    """测试 AI 评分服务配置"""
    from app.core.config import settings

    # 验证 AI 服务配置存在
    assert hasattr(settings, 'AI_SERVICE_URL')
    assert hasattr(settings, 'AI_SERVICE_TIMEOUT')
    assert settings.AI_SERVICE_URL is not None
    assert settings.AI_SERVICE_TIMEOUT > 0

    print("✅ test_ai_scoring_service_config 通过")


def test_error_handling_integration():
    """测试异常处理机制"""
    from app.services.ai_scoring_service import AIScoringService
    import inspect

    source = inspect.getsource(AIScoringService.evaluate_scoring)

    # 验证包含异常处理
    assert "try" in source
    assert "except" in source
    assert "BusinessException" in source or "Exception" in source

    print("✅ test_error_handling_integration 通过")


def main():
    print("=" * 60)
    print("Backend 端 AI 评分集成测试")
    print("=" * 60)
    print()

    tests = [
        ("AI 评分服务存在", test_ai_scoring_service_exists),
        ("AI 评分服务接口", test_ai_scoring_service_interface),
        ("AI 评分方法", test_grading_service_ai_grade_method),
        ("保存 AI 评分方法", test_grading_service_save_ai_score_method),
        ("AnswerRecord AI 字段", test_answer_record_model_has_ai_fields),
        ("自动评分支持 AI", test_grading_service_auto_grade_supports_ai),
        ("评分详情包含 AI 信息", test_grading_result_detail_includes_ai_info),
        ("AI 服务配置", test_ai_scoring_service_config),
        ("异常处理机制", test_error_handling_integration),
    ]

    errors = []
    for name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name} 失败: {e}")

    print()
    print("=" * 60)
    total = len(tests)
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
