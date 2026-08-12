"""
评分 Agent
职责：根据题目、标准答案、评分规则、用户答案，给出 AI 评分

支持场景：
- 高质量答案（完整、准确）
- 部分正确答案（有瑕疵但主要要点覆盖）
- 错误答案（不相关或错误）
- 空答案（返回 0 分）
- 异常返回（JSON 解析失败时返回默认值）

支持 Prompt 版本：
- v1: 基础评分，返回 score/reason/missing_points/confidence
- v2: 增强评分，增加 matched_points（知识点分析）
- v3: 精准评分，增加 score_level/question_type/keyword_coverage（题型自适应+知识点覆盖率）
"""
import json
import re
import time
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.config import load_prompt, render_prompt
from app.core.logger import get_logger, log_ai_error, log_ai_request, log_ai_response, Timer
from app.llm.client import LLMClient

logger = get_logger(__name__)

# 低置信度阈值：低于此值的评分结果需要人工复核
LOW_CONFIDENCE_THRESHOLD = 0.6


class ScoringAgent(BaseAgent):
    """主观题评分 Agent"""

    def __init__(self, llm_client: LLMClient, prompt_version: str = "v3"):
        self.llm_client = llm_client
        self.prompt_version = prompt_version
        self.prompt = load_prompt("scoring", prompt_version)

    def validate_input(
        self,
        question: str,
        standard_answer: str,
        user_answer: str,
        max_score: float = 10.0,
        scoring_rules: str = "",
    ) -> bool:
        """校验输入参数"""
        if not question or not question.strip():
            return False
        if not user_answer or not user_answer.strip():
            return False
        if max_score <= 0:
            return False
        return True

    async def run(
        self,
        question: str,
        standard_answer: str,
        user_answer: str,
        max_score: float = 10.0,
        scoring_rules: str = "",
    ) -> dict[str, Any]:
        """执行评分

        Args:
            question: 题目内容
            standard_answer: 标准答案
            user_answer: 用户答案
            max_score: 满分
            scoring_rules: 评分规则

        Returns:
            dict: {
                score: float, 得分 (0 ~ max_score)
                reason: str, 评分理由
                matched_points: list[str], 匹配的知识点
                missing_points: list[str], 遗漏要点
                confidence: float, 置信度 (0-1)
                needs_review: bool, 是否需要人工复核
                prompt_version: str, 使用的 Prompt 版本
                score_level: str, 评分等级 (v3: full_correct/partial_correct/incorrect)
                question_type: str, 题型 (v3: short_answer/concept/analysis)
                keyword_coverage: float, 知识点覆盖率 (v3)
            }

        Raises:
            ValueError: 输入校验失败
            RuntimeError: LLM 调用失败
        """
        # 1. 输入校验
        if not self.validate_input(
            question, standard_answer, user_answer, max_score, scoring_rules
        ):
            raise ValueError("输入参数校验失败：题目和用户答案不能为空")

        # 2. 空答案快速处理
        if not user_answer or not user_answer.strip():
            result = {
                "score": 0.0,
                "reason": "候选人未作答",
                "missing_points": ["全部要点"],
                "matched_points": [],
                "confidence": 1.0,
                "needs_review": False,
                "prompt_version": self.prompt.version,
                "score_level": "incorrect",
                "question_type": "short_answer",
                "keyword_coverage": 0.0,
            }
            return result

        # 3. 渲染 Prompt
        prompt_text = render_prompt(
            self.prompt,
            question=question,
            standard_answer=standard_answer or "（无标准答案）",
            scoring_rules=scoring_rules or "（无特殊评分规则）",
            user_answer=user_answer,
            max_score=max_score,
        )

        # 4. 构造消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的考试阅卷助手，请严格按照要求输出 JSON 格式。",
            },
            {"role": "user", "content": prompt_text},
        ]

        # 5. 调用 LLM
        model_name = getattr(self.llm_client, "model", "unknown")
        with Timer() as timer:
            try:
                log_ai_request(
                    endpoint="scoring/evaluate",
                    model=model_name,
                    prompt_version=self.prompt.version,
                    input_size=len(prompt_text),
                )
                raw_response = await self.llm_client.chat(
                    messages, temperature=0.3, max_tokens=1024
                )
            except Exception as e:
                log_ai_error(
                    endpoint="scoring/evaluate",
                    error_type=type(e).__name__,
                    error_msg=str(e),
                    latency_ms=max(0, timer.elapsed_ms),
                )
                raise RuntimeError(f"LLM 调用失败: {e}")

        # 6. 解析响应
        result = self._parse_response(raw_response, max_score)

        # 7. 添加元信息
        result["needs_review"] = result.get("confidence", 0) < LOW_CONFIDENCE_THRESHOLD
        result["prompt_version"] = self.prompt.version

        # 8. v3: 自动计算score_level（如果LLM未提供）
        if not result.get("score_level"):
            result["score_level"] = self._calculate_score_level(
                result["score"], max_score
            )

        # 9. v3: 默认question_type和keyword_coverage
        if not result.get("question_type"):
            result["question_type"] = "short_answer"
        if not result.get("keyword_coverage"):
            result["keyword_coverage"] = self._estimate_keyword_coverage(result)

        log_ai_response(
            endpoint="scoring/evaluate",
            status="success",
            latency_ms=timer.elapsed_ms,
            output_size=len(raw_response),
        )
        logger.info(
            f"AI 评分完成: score={result['score']}, confidence={result['confidence']:.2f}, "
            f"score_level={result['score_level']}, needs_review={result['needs_review']}, "
            f"latency_ms={timer.elapsed_ms:.1f}"
        )

        return result

    def _parse_response(self, raw_response: str, max_score: float) -> dict[str, Any]:
        """解析 LLM 返回的 JSON 响应

        处理策略：
        1. 直接尝试 JSON 解析
        2. 提取 JSON 块后解析
        3. 失败则返回默认值（0 分 + 低置信度）

        Args:
            raw_response: LLM 原始响应
            max_score: 满分

        Returns:
            dict: 评分结果
        """
        # 清理响应文本，提取 JSON
        cleaned = self._extract_json(raw_response)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # 解析失败，返回默认值
            return {
                "score": 0.0,
                "reason": "AI 响应格式错误，无法解析",
                "matched_points": [],
                "missing_points": [],
                "confidence": 0.0,
                "score_level": "incorrect",
                "question_type": "short_answer",
                "keyword_coverage": 0.0,
            }

        # 提取字段，设置默认值
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))
        matched_points = data.get("matched_points", [])
        missing_points = data.get("missing_points", [])
        confidence = float(data.get("confidence", 0))
        score_level = data.get("score_level", "")
        question_type = data.get("question_type", "")
        keyword_coverage = data.get("keyword_coverage", None)

        # 分数范围限制 (0 ~ max_score)
        score = max(0.0, min(score, max_score))
        # 置信度范围限制 (0 ~ 1)
        confidence = max(0.0, min(confidence, 1.0))

        # 验证数据类型
        if not isinstance(matched_points, list):
            matched_points = [str(matched_points)] if matched_points else []
        if not isinstance(missing_points, list):
            missing_points = [str(missing_points)] if missing_points else []

        # 空列表处理
        if isinstance(matched_points, list) and len(matched_points) == 0:
            matched_points = []
        if isinstance(missing_points, list) and len(missing_points) == 0:
            missing_points = []

        # v3: 验证score_level
        valid_levels = ["full_correct", "partial_correct", "incorrect"]
        if score_level not in valid_levels:
            score_level = ""

        # v3: 验证question_type
        valid_types = ["short_answer", "concept", "analysis"]
        if question_type not in valid_types:
            question_type = ""

        # v3: 验证keyword_coverage
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
            "score_level": score_level,
            "question_type": question_type,
            "keyword_coverage": keyword_coverage,
        }

    @staticmethod
    def _calculate_score_level(score: float, max_score: float) -> str:
        """根据分数比例计算评分等级

        Args:
            score: 实际得分
            max_score: 满分

        Returns:
            str: full_correct / partial_correct / incorrect
        """
        if max_score <= 0:
            return "incorrect"

        ratio = score / max_score

        if ratio >= 0.9:
            return "full_correct"
        elif ratio >= 0.6:
            return "partial_correct"
        else:
            return "incorrect"

    @staticmethod
    def _estimate_keyword_coverage(result: dict) -> float:
        """根据匹配/缺失知识点估算覆盖率

        Args:
            result: 评分结果

        Returns:
            float: 估算的知识点覆盖率 (0-1)
        """
        matched = result.get("matched_points", [])
        missing = result.get("missing_points", [])

        total = len(matched) + len(missing)
        if total == 0:
            return 0.0

        return len(matched) / total

    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取 JSON 块

        支持格式：
        - 纯 JSON: {"key": "value"}
        - 代码块: ```json\n{...}\n```
        - 带文本: 一些文字 { "key": "value" } 更多文字

        Args:
            text: 原始文本

        Returns:
            str: 提取的 JSON 字符串
        """
        # 尝试匹配代码块
        code_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            text,
            re.DOTALL,
        )
        if code_block_match:
            return code_block_match.group(1).strip()

        # 尝试提取花括号内容
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        # 返回原文，让 JSON 解析器处理
        return text.strip()
