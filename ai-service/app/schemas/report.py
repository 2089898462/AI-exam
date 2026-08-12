"""
报告相关 Schema 定义
"""
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """报告生成请求"""
    exam_results: str = Field(
        ...,
        min_length=1,
        description="考试结果数据 (JSON 字符串)",
    )
    exam_title: str = Field(default="", description="考试标题")
    candidate_name: str = Field(default="", description="候选人姓名")
    position: str = Field(default="", description="应聘岗位")


class ReportGenerateResponse(BaseModel):
    """报告生成响应"""
    summary: str = Field(..., description="总体评价")
    strengths: list[str] = Field(default_factory=list, description="优势能力")
    weaknesses: list[str] = Field(default_factory=list, description="薄弱能力")
    skill_analysis: dict = Field(default_factory=dict, description="各能力维度分析")
    interview_suggestions: list[str] = Field(
        default_factory=list, description="面试建议"
    )
    recommendation: str = Field(default="保留考虑", description="招聘建议")
    prompt_version: str = Field(default="1.0", description="使用的 Prompt 版本")
