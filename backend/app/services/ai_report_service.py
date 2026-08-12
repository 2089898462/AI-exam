"""
AI 报告 Service
负责调用 AI-Service 生成考试分析报告，并保存到数据库

调用链路：
Backend (ai_report_service) → HTTP Client → AI-Service (/api/report/generate)
  → ReportAgent → LLMClient → LLM API

异常处理：
- 服务不可用：ConnectionError
- 请求超时：TimeoutError
- 返回格式错误：ValueError
"""
import json
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.exceptions import BusinessException, NotFoundException
from app.models.ai_report import AiReport

logger = get_logger(__name__)


class AIReportService:
    """AI 报告服务"""

    def __init__(self):
        self.base_url = settings.AI_SERVICE_URL
        self.timeout = settings.AI_SERVICE_TIMEOUT

    def generate_report(
        self,
        exam_results: str,
        exam_title: str = "",
        candidate_name: str = "",
        position: str = "",
        prompt_version: str = "1.0",
    ) -> dict:
        """调用 AI-Service 生成报告

        Args:
            exam_results: 考试结果数据 (JSON 字符串)
            exam_title: 考试标题
            candidate_name: 候选人姓名
            position: 应聘岗位
            prompt_version: Prompt 版本

        Returns:
            dict: 报告生成结果
        """
        url = f"{self.base_url}/api/report/generate"

        payload = {
            "exam_results": exam_results,
            "exam_title": exam_title,
            "candidate_name": candidate_name,
            "position": position,
            "prompt_version": prompt_version,
        }

        try:
            _start = time.perf_counter()
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            _elapsed = (time.perf_counter() - _start) * 1000

            data = response.json()
            result = self._validate_response(data)
            logger.info(
                f"AI 报告生成成功: recommendation={result['recommendation']}, "
                f"prompt_version={result.get('prompt_version')}, elapsed_ms={_elapsed:.1f}"
            )
            return result

        except httpx.ConnectError:
            logger.error(f"AI 报告服务不可用: url={url}")
            raise BusinessException(
                "AI 报告服务不可用，请稍后重试",
                error_code="AI_REPORT_SERVICE_UNAVAILABLE",
            )
        except httpx.TimeoutException:
            raise BusinessException(
                f"AI 报告请求超时（{self.timeout}秒），请稍后重试",
                error_code="AI_REPORT_TIMEOUT",
            )
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if e.response.status_code == 400:
                raise BusinessException(
                    f"AI 报告请求参数错误: {error_detail}",
                    error_code="AI_REPORT_BAD_REQUEST",
                )
            elif e.response.status_code == 500:
                raise BusinessException(
                    f"AI 报告服务内部错误: {error_detail}",
                    error_code="AI_REPORT_INTERNAL_ERROR",
                )
            else:
                raise BusinessException(
                    f"AI 报告请求失败（状态码: {e.response.status_code}）",
                    error_code="AI_REPORT_HTTP_ERROR",
                )
        except ValueError as e:
            raise BusinessException(
                f"AI 报告返回数据格式错误: {e}",
                error_code="AI_REPORT_FORMAT_ERROR",
            )
        except Exception as e:
            raise BusinessException(
                f"AI 报告调用异常: {e}",
                error_code="AI_REPORT_UNKNOWN_ERROR",
            )

    def _validate_response(self, data: dict) -> dict:
        """验证 AI-Service 返回的报告数据"""
        required_fields = [
            "summary", "strengths", "weaknesses",
            "skill_analysis", "interview_suggestions", "recommendation"
        ]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            raise ValueError(f"AI 返回报告数据缺少必要字段: {missing_fields}")

        # 类型校验和修正
        strengths = data["strengths"]
        if not isinstance(strengths, list):
            strengths = [str(strengths)] if strengths else []

        weaknesses = data["weaknesses"]
        if not isinstance(weaknesses, list):
            weaknesses = [str(weaknesses)] if weaknesses else []

        skill_analysis = data["skill_analysis"]
        if not isinstance(skill_analysis, dict):
            skill_analysis = {"综合能力": str(skill_analysis)}

        interview_suggestions = data["interview_suggestions"]
        if not isinstance(interview_suggestions, list):
            interview_suggestions = [str(interview_suggestions)] if interview_suggestions else []

        # 标准化 recommendation
        valid_recommendations = ["强烈推荐", "推荐", "保留考虑", "不推荐"]
        recommendation = str(data["recommendation"])
        if recommendation not in valid_recommendations:
            recommendation = "保留考虑"

        return {
            "summary": str(data["summary"]),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "skill_analysis": skill_analysis,
            "interview_suggestions": interview_suggestions,
            "recommendation": recommendation,
            "prompt_version": data.get("prompt_version", "1.0"),
        }

    def check_service_health(self) -> bool:
        """检查 AI-Service 健康状态"""
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False


# 全局实例
ai_report_service = AIReportService()
