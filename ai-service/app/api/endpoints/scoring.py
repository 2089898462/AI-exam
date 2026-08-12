"""
评分 API 端点
供 Backend 调用的 AI 评分接口
支持 v1 (基础评分) 和 v2 (增强评分+知识点分析) 两种 Prompt 版本
"""
from fastapi import APIRouter, HTTPException

from app.llm.client import LLMClient
from app.llm.models import ModelConfig
from app.agents.scoring_agent import ScoringAgent
from app.core.config import config as ai_config
from app.schemas.scoring import ScoringRequest, ScoringResponse

router = APIRouter()


def _create_llm_client() -> LLMClient:
    """创建 LLM 客户端"""
    config = ModelConfig(
        name=ai_config.MODEL_NAME,
        provider=ai_config.MODEL_PROVIDER,
        api_key=ai_config.API_KEY,
        api_base=ai_config.API_BASE,
        max_tokens=ai_config.MAX_TOKENS,
        temperature=ai_config.TEMPERATURE,
    )
    return LLMClient(config)


@router.post("/evaluate", response_model=ScoringResponse)
async def evaluate_scoring(request: ScoringRequest):
    """执行 AI 评分

    接收题目信息和用户答案，返回结构化评分结果。
    支持 v1、v2 和 v3 三种 Prompt 版本。

    v1 返回: score, reason, missing_points, confidence
    v2 增加: matched_points (知识点分析), needs_review
    v3 增加: score_level, question_type, keyword_coverage

    - score: 得分 (0 ~ max_score)
    - reason: 评分理由
    - matched_points: 覆盖的关键知识点 (v2)
    - missing_points: 遗漏要点列表
    - confidence: 置信度 (0-1)
    - score_level: 评分等级 (v3)
    - question_type: 题型 (v3)
    - keyword_coverage: 知识点覆盖率 (v3)
    """
    llm_client = _create_llm_client()

    try:
        agent = ScoringAgent(llm_client, prompt_version=request.prompt_version)

        result = await agent.run(
            question=request.question,
            standard_answer=request.standard_answer,
            user_answer=request.user_answer,
            max_score=request.max_score,
            scoring_rules=request.scoring_rules or "",
        )

        return ScoringResponse(
            score=result["score"],
            reason=result["reason"],
            matched_points=result.get("matched_points", []),
            missing_points=result.get("missing_points", []),
            confidence=result["confidence"],
            prompt_version=result.get("prompt_version", request.prompt_version),
            needs_review=result.get("needs_review", False),
            score_level=result.get("score_level", ""),
            question_type=result.get("question_type", ""),
            keyword_coverage=result.get("keyword_coverage"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评分服务内部错误: {e}")
    finally:
        await llm_client.close()
