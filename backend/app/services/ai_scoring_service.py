"""
AI 评分 Service
负责调用 AI-Service 执行主观题评分

调用链路：
Backend (ai_scoring_service) → HTTP Client → AI-Service (/api/v1/scoring/evaluate)
  → ScoringAgent → LLMClient → LLM API

异常处理：
- 服务不可用：ConnectionError
- 请求超时：TimeoutError
- 返回格式错误：ValueError
"""
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.exceptions import BusinessException

logger = get_logger(__name__)


class AIScoringService:
    """AI 评分服务"""

    def __init__(self):
        self.base_url = settings.AI_SERVICE_URL
        self.timeout = settings.AI_SERVICE_TIMEOUT

    def evaluate_scoring(
        self,
        question: str,
        standard_answer: str = "",
        user_answer: str = "",
        max_score: float = 10.0,
        scoring_rules: Optional[str] = None,
        prompt_version: str = "v3",
    ) -> dict:
        """调用 AI-Service 执行评分

        Args:
            question: 题目内容
            standard_answer: 标准答案
            user_answer: 用户答案
            max_score: 满分
            scoring_rules: 评分规则
            prompt_version: Prompt 版本

        Returns:
            dict: {
                score: float, 得分
                reason: str, 评分理由
                missing_points: list[str], 遗漏要点
                confidence: float, 置信度
            }

        Raises:
            BusinessException: AI 评分失败
        """
        url = f"{self.base_url}/api/scoring/evaluate"

        payload = {
            "question": question,
            "standard_answer": standard_answer,
            "user_answer": user_answer,
            "max_score": max_score,
            "scoring_rules": scoring_rules,
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
                f"AI 评分成功: score={result['score']}, confidence={result['confidence']:.2f}, "
                f"elapsed_ms={_elapsed:.1f}"
            )
            return result
        except httpx.ConnectError as e:
            logger.error(f"AI 评分服务不可用: url={url}")
            raise BusinessException(
                f"AI 评分服务不可用，请稍后重试",
                error_code="AI_SERVICE_UNAVAILABLE",
            )
        except httpx.TimeoutException as e:
            raise BusinessException(
                f"AI 评分请求超时（{self.timeout}秒），请稍后重试",
                error_code="AI_SERVICE_TIMEOUT",
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
                    f"AI 评分请求参数错误: {error_detail}",
                    error_code="AI_SCORING_BAD_REQUEST",
                )
            elif e.response.status_code == 500:
                raise BusinessException(
                    f"AI 评分服务内部错误: {error_detail}",
                    error_code="AI_SCORING_INTERNAL_ERROR",
                )
            else:
                raise BusinessException(
                    f"AI 评分请求失败（状态码: {e.response.status_code}）",
                    error_code="AI_SCORING_HTTP_ERROR",
                )
        except ValueError as e:
            raise BusinessException(
                f"AI 评分返回数据格式错误: {e}",
                error_code="AI_SCORING_FORMAT_ERROR",
            )
        except Exception as e:
            raise BusinessException(
                f"AI 评分调用异常: {e}",
                error_code="AI_SCORING_UNKNOWN_ERROR",
            )

    def _validate_response(self, data: dict) -> dict:
        """验证 AI-Service 返回的数据格式

        Args:
            data: AI-Service 返回的 JSON 数据

        Returns:
            dict: 验证后的评分结果

        Raises:
            ValueError: 数据格式错误
        """
        required_fields = ["score", "reason", "confidence"]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            raise ValueError(f"AI 返回数据缺少必要字段: {missing_fields}")

        # 字段类型校验
        score = float(data["score"])
        reason = str(data["reason"])
        confidence = float(data["confidence"])

        # 可选字段
        missing_points = data.get("missing_points", [])
        matched_points = data.get("matched_points", [])
        prompt_version = data.get("prompt_version", "v3")
        needs_review = data.get("needs_review", False)
        score_level = data.get("score_level", "")
        question_type = data.get("question_type", "")
        keyword_coverage = data.get("keyword_coverage", None)

        # 范围校验
        if score < 0:
            score = 0.0
        if confidence < 0 or confidence > 1:
            confidence = max(0.0, min(confidence, 1.0))

        # 类型校验
        if not isinstance(missing_points, list):
            missing_points = [str(missing_points)] if missing_points else []
        if not isinstance(matched_points, list):
            matched_points = [str(matched_points)] if matched_points else []

        # v3字段校验
        valid_levels = ["full_correct", "partial_correct", "incorrect"]
        if score_level not in valid_levels:
            score_level = ""

        valid_types = ["short_answer", "concept", "analysis"]
        if question_type not in valid_types:
            question_type = ""

        if keyword_coverage is not None:
            try:
                keyword_coverage = float(keyword_coverage)
                keyword_coverage = max(0.0, min(keyword_coverage, 1.0))
            except (ValueError, TypeError):
                keyword_coverage = None

        return {
            "score": score,
            "reason": reason,
            "matched_points": matched_points,
            "missing_points": missing_points,
            "confidence": confidence,
            "prompt_version": prompt_version,
            "needs_review": needs_review,
            "score_level": score_level,
            "question_type": question_type,
            "keyword_coverage": keyword_coverage,
        }

    def check_service_health(self) -> bool:
        """检查 AI-Service 健康状态

        Returns:
            bool: 服务是否可用
        """
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False


# 全局实例
ai_scoring_service = AIScoringService()
