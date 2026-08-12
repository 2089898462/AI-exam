"""
报告生成 API 端点
供 Backend 调用的 AI 报告生成接口
"""
from fastapi import APIRouter, HTTPException

from app.llm.client import LLMClient
from app.llm.models import ModelConfig
from app.agents.report_agent import ReportAgent
from app.core.config import config as ai_config
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse

router = APIRouter()


def _create_llm_client() -> LLMClient:
    """创建 LLM 客户端"""
    model_config = ModelConfig(
        name=ai_config.MODEL_NAME,
        provider=ai_config.MODEL_PROVIDER,
        max_tokens=ai_config.MAX_TOKENS,
        temperature=ai_config.TEMPERATURE,
        api_key=ai_config.API_KEY,
        api_base=ai_config.API_BASE,
    )
    return LLMClient(model_config)


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(request: ReportGenerateRequest):
    """生成 AI 能力分析报告

    接收考试结果数据，返回结构化能力分析报告。

    - summary: 总体评价
    - strengths: 优势能力
    - weaknesses: 薄弱能力
    - skill_analysis: 各维度分析
    - interview_suggestions: 面试建议
    - recommendation: 招聘建议
    """
    llm_client = _create_llm_client()
    agent = ReportAgent(llm_client)

    try:
        result = await agent.run(
            exam_results=request.exam_results,
            exam_title=request.exam_title or "",
            candidate_name=request.candidate_name or "",
            position=request.position or "",
        )

        return ReportGenerateResponse(
            summary=result["summary"],
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
            skill_analysis=result["skill_analysis"],
            interview_suggestions=result["interview_suggestions"],
            recommendation=result["recommendation"],
            prompt_version=result.get("prompt_version", "1.0"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成服务内部错误: {e}")
    finally:
        await llm_client.close()
