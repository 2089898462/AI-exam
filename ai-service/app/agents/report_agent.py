"""
报告 Agent
职责：根据考试结果生成能力分析报告

输出结构：
- summary: 总体评价
- strengths: 优势能力列表
- weaknesses: 薄弱能力列表
- skill_analysis: 各能力维度分析
- interview_suggestions: 面试建议
- recommendation: 招聘建议
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


class ReportAgent(BaseAgent):
    """能力分析报告 Agent"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.prompt = load_prompt("report", "v1")

    def validate_input(
        self,
        exam_results: str,
        exam_title: str = "",
        candidate_name: str = "",
        position: str = "",
    ) -> bool:
        """校验输入参数"""
        if not exam_results or not exam_results.strip():
            return False
        return True

    async def run(
        self,
        exam_results: str,
        exam_title: str = "",
        candidate_name: str = "",
        position: str = "",
    ) -> dict[str, Any]:
        """执行报告生成

        Args:
            exam_results: 考试结果数据 (JSON 字符串)
            exam_title: 考试标题
            candidate_name: 候选人姓名
            position: 应聘岗位

        Returns:
            dict: {
                summary: str,
                strengths: list[str],
                weaknesses: list[str],
                skill_analysis: dict,
                interview_suggestions: list[str],
                recommendation: str,
                prompt_version: str,
            }
        """
        # 1. 输入校验
        if not self.validate_input(exam_results, exam_title, candidate_name, position):
            raise ValueError("输入参数校验失败：考试结果数据不能为空")

        # 2. 渲染 Prompt
        prompt_text = render_prompt(
            self.prompt,
            exam_results=exam_results,
            exam_title=exam_title or "未知考试",
            candidate_name=candidate_name or "候选人",
            position=position or "未知岗位",
        )

        # 3. 构造消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的人力资源能力分析专家，请严格按照要求输出 JSON 格式。",
            },
            {"role": "user", "content": prompt_text},
        ]

        # 4. 调用 LLM
        model_name = getattr(self.llm_client, "model", "unknown")
        with Timer() as timer:
            try:
                log_ai_request(
                    endpoint="report/generate",
                    model=model_name,
                    prompt_version=self.prompt.version,
                    input_size=len(prompt_text),
                )
                raw_response = await self.llm_client.chat(
                    messages, temperature=0.5, max_tokens=2048
                )
            except Exception as e:
                log_ai_error(
                    endpoint="report/generate",
                    error_type=type(e).__name__,
                    error_msg=str(e),
                    latency_ms=max(0, timer.elapsed_ms),
                )
                raise RuntimeError(f"LLM 调用失败: {e}")

        # 5. 解析响应
        result = self._parse_response(raw_response)

        # 6. 添加元信息
        result["prompt_version"] = self.prompt.version

        log_ai_response(
            endpoint="report/generate",
            status="success",
            latency_ms=timer.elapsed_ms,
            output_size=len(raw_response),
        )
        logger.info(
            f"AI 报告生成完成: recommendation={result['recommendation']}, "
            f"latency_ms={timer.elapsed_ms:.1f}"
        )

        return result

    def _parse_response(self, raw_response: str) -> dict[str, Any]:
        """解析 LLM 返回的 JSON 响应"""
        cleaned = self._extract_json(raw_response)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return self._default_result("AI 响应格式错误，无法解析")

        # 提取字段
        summary = str(data.get("summary", ""))
        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        skill_analysis = data.get("skill_analysis", {})
        interview_suggestions = data.get("interview_suggestions", [])
        recommendation = str(data.get("recommendation", "保留考虑"))

        # 类型校验和修正
        if not isinstance(strengths, list):
            strengths = [str(strengths)] if strengths else []
        if not isinstance(weaknesses, list):
            weaknesses = [str(weaknesses)] if weaknesses else []
        if not isinstance(skill_analysis, dict):
            skill_analysis = {"综合能力": str(skill_analysis)}
        if not isinstance(interview_suggestions, list):
            interview_suggestions = [str(interview_suggestions)] if interview_suggestions else []

        # 限制 summary 长度
        if len(summary) > 100:
            summary = summary[:100] + "..."

        # 标准化 recommendation
        valid_recommendations = ["强烈推荐", "推荐", "保留考虑", "不推荐"]
        if recommendation not in valid_recommendations:
            recommendation = "保留考虑"

        return {
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "skill_analysis": skill_analysis,
            "interview_suggestions": interview_suggestions,
            "recommendation": recommendation,
        }

    @staticmethod
    def _default_result(reason: str = "") -> dict[str, Any]:
        """返回默认报告结果（解析失败时使用）"""
        return {
            "summary": f"报告生成失败：{reason}",
            "strengths": [],
            "weaknesses": [],
            "skill_analysis": {},
            "interview_suggestions": ["建议重新生成报告"],
            "recommendation": "保留考虑",
        }

    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取 JSON 块（支持嵌套结构）"""
        # 尝试匹配代码块
        code_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            text,
            re.DOTALL,
        )
        if code_block_match:
            return code_block_match.group(1).strip()

        # 找到第一个 { 并追踪到匹配的 }
        start = text.find("{")
        if start == -1:
            return text.strip()

        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return text.strip()
