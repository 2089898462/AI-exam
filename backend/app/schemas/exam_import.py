"""
考试导入 Schema
用于校验 JSON 导入数据
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class OptionImportSchema(BaseModel):
    label: str = Field(..., min_length=1, max_length=10, description="选项标签，如 A/B/C/D")
    text: str = Field(..., min_length=1, max_length=500, description="选项内容")


class QuestionImportSchema(BaseModel):
    type: str = Field(..., pattern="^(single_choice|multiple_choice|essay|short_answer)$", description="题型")
    content: str = Field(..., min_length=1, max_length=5000, description="题目内容")
    question_no: Optional[int | str] = Field(None, description="题目编号")
    category: Optional[str] = Field(None, max_length=50, description="题目分类")
    options: Optional[list[OptionImportSchema]] = Field(None, description="选项列表（选择题必填）")
    answer: str = Field(..., min_length=1, max_length=2000, description="标准答案")
    score: float = Field(default=0, ge=0, description="分值")
    sort_order: int = Field(default=0, ge=0, description="排序序号")

    @field_validator("question_no")
    @classmethod
    def normalize_question_no(cls, v: int | str | None) -> str | None:
        """将数字类型的 question_no 转换为字符串"""
        if v is None:
            return None
        s = str(v)
        if len(s) > 20:
            raise ValueError("题目编号长度不能超过 20 个字符")
        return s

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """统一题型命名"""
        type_map = {"short_answer": "essay", "essay": "essay"}
        return type_map.get(v, v)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list | None, info) -> list | None:
        q_type = info.data.get("type")
        if q_type in ("single_choice", "multiple_choice"):
            if not v or len(v) < 2:
                raise ValueError(f"{q_type} 题型至少需要 2 个选项")
            labels = [opt.label for opt in v]
            if len(labels) != len(set(labels)):
                raise ValueError("选项标签不能重复")
        return v

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str, info) -> str:
        q_type = info.data.get("type")
        options = info.data.get("options")

        if q_type == "single_choice":
            if not options:
                raise ValueError("单选题必须提供选项")
            labels = [opt.label for opt in options]
            if v not in labels:
                raise ValueError(f"答案 '{v}' 不在选项列表中，可选值: {labels}")

        elif q_type == "multiple_choice":
            if not options:
                raise ValueError("多选题必须提供选项")
            labels = [opt.label for opt in options]
            answer_labels = [a.strip() for a in v.split(",")]
            if len(answer_labels) < 2:
                raise ValueError("多选题至少需要选择 2 个答案")
            for al in answer_labels:
                if al not in labels:
                    raise ValueError(f"答案 '{al}' 不在选项列表中，可选值: {labels}")

        elif q_type == "essay":
            if not v.strip():
                raise ValueError("问答题答案不能为空")

        return v

    @model_validator(mode="after")
    def validate_question(self) -> "QuestionImportSchema":
        if self.type == "essay" and self.options is not None:
            pass
        return self


class ExamImportSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="考试名称")
    description: Optional[str] = Field(None, max_length=500, description="考试说明")
    duration_minutes: int = Field(..., gt=0, le=1440, description="考试时长（分钟）")
    pass_score: float = Field(default=0, ge=0, description="及格分数")
    exam_code: Optional[str] = Field(None, max_length=50, description="考试编号")
    position: Optional[str] = Field(None, max_length=100, description="岗位")
    questions: list[QuestionImportSchema] = Field(..., min_length=1, description="题目列表")


class ImportResult(BaseModel):
    imported_count: int = Field(..., description="成功导入的题目数量")
    exam_id: int = Field(..., description="考试 ID")
    exam_title: str = Field(..., description="考试名称")


class ImportErrorDetail(BaseModel):
    errors: list[str] = Field(default_factory=list, description="错误详情列表")