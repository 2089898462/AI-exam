"""
客观题评分模块
支持单选题、多选题、判断题的自动评分

评分规则：
- single_choice: 候选人答案完全匹配标准答案 → 得分
- multiple_choice: 候选人答案与标准答案完全匹配（顺序无关）→ 得分
- true_false: 候选人答案完全匹配标准答案 → 得分
"""
import re
from typing import Optional


# 支持评分的题型
_GRADEABLE_TYPES = {"single_choice", "multiple_choice", "true_false"}


def is_objective_question(question_type: str) -> bool:
    """判断是否为客观题（可自动评分）"""
    return question_type in _GRADEABLE_TYPES


def grade_question(
    question_type: str,
    candidate_answer: Optional[str],
    standard_answer: str,
    full_score: float,
) -> tuple[float, bool]:
    """评分单道客观题

    Args:
        question_type: 题型 (single_choice, multiple_choice, true_false)
        candidate_answer: 候选人答案
        standard_answer: 标准答案
        full_score: 满分

    Returns:
        tuple[float, bool]: (得分, 是否正确)
    """
    if question_type not in _GRADEABLE_TYPES:
        return 0.0, False

    # 空答案处理
    if not candidate_answer or not candidate_answer.strip():
        return 0.0, False

    if question_type == "single_choice":
        return _grade_single_choice(candidate_answer, standard_answer, full_score)
    elif question_type == "multiple_choice":
        return _grade_multiple_choice(candidate_answer, standard_answer, full_score)
    elif question_type == "true_false":
        return _grade_true_false(candidate_answer, standard_answer, full_score)
    else:
        return 0.0, False


def _normalize_answer(answer: str) -> str:
    """规范化答案格式

    处理以下格式：
    - "A" → "A"
    - "A,B,C" → "A,B,C"
    - "A B C" → "A,B,C"
    - "[A, B, C]" → "A,B,C"
    - '["A", "B", "C"]' → "A,B,C"

    返回大写的选项标签字符串
    """
    if not answer:
        return ""

    # 移除多余字符
    cleaned = answer.strip().upper()

    # 如果是列表格式 JSON，尝试解析
    if cleaned.startswith("[") or cleaned.startswith("'["):
        try:
            import json
            # 尝试清理并解析
            json_str = cleaned
            if not json_str.startswith("["):
                json_str = json_str[1:] if json_str.startswith("'") else json_str
            items = json.loads(json_str)
            if isinstance(items, list):
                items = [str(item).strip().upper() for item in items]
                return ",".join(sorted(items))
        except (json.JSONDecodeError, ValueError):
            pass

    # 移除方括号和引号
    cleaned = re.sub(r'[\[\]\'"\s]', ',', cleaned)

    # 分割并清理
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    if not parts:
        return ""

    # 去重并排序
    unique_parts = sorted(set(parts))
    return ",".join(unique_parts)


def _grade_single_choice(
    candidate_answer: str,
    standard_answer: str,
    full_score: float,
) -> tuple[float, bool]:
    """单选题评分

    比对规则：候选人答案与标准答案完全匹配（忽略大小写和空格）
    """
    candidate = candidate_answer.strip().upper()
    standard = standard_answer.strip().upper()

    if candidate == standard:
        return full_score, True
    else:
        return 0.0, False


def _grade_multiple_choice(
    candidate_answer: str,
    standard_answer: str,
    full_score: float,
) -> tuple[float, bool]:
    """多选题评分

    比对规则：候选人答案与标准答案完全匹配（顺序无关，忽略大小写和空格）
    """
    candidate_norm = _normalize_answer(candidate_answer)
    standard_norm = _normalize_answer(standard_answer)

    if not candidate_norm or not standard_norm:
        return 0.0, False

    if candidate_norm == standard_norm:
        return full_score, True
    else:
        return 0.0, False


def _grade_true_false(
    candidate_answer: str,
    standard_answer: str,
    full_score: float,
) -> tuple[float, bool]:
    """判断题评分

    比对规则：
    - 标准答案 "true" → 候选人答案为 "true" 或 "正确"
    - 标准答案 "false" → 候选人答案为 "false" 或 "错误"
    """
    candidate = candidate_answer.strip().lower()
    standard = standard_answer.strip().lower()

    # 标准化处理
    true_values = {"true", "正确", "对", "√", "yes", "t"}
    false_values = {"false", "错误", "错", "×", "no", "f"}

    candidate_binary = "true" if candidate in true_values else ("false" if candidate in false_values else None)
    standard_binary = "true" if standard in true_values else ("false" if standard in false_values else None)

    if candidate_binary is None or standard_binary is None:
        return 0.0, False

    if candidate_binary == standard_binary:
        return full_score, True
    else:
        return 0.0, False


def calculate_auto_score(
    answers: list[dict],
    questions: dict[int, dict],
) -> tuple[float, int, int, int]:
    """批量计算客观题得分

    Args:
        answers: 答题记录列表 [{question_id, answer_content, score, is_correct}]
        questions: 题目字典 {question_id: {type, answer, score}}

    Returns:
        tuple[float, int, int, int]: (总分, 答题数, 正确数, 未答数)
    """
    total_score = 0.0
    answered_count = 0
    correct_count = 0
    unanswered_count = 0

    for answer in answers:
        question_id = answer["question_id"]
        if question_id not in questions:
            continue

        question = questions[question_id]
        question_type = question["type"]
        candidate_answer = answer.get("answer_content")
        standard_answer = question["answer"]
        full_score = question["score"]

        # 空答案统计
        if not candidate_answer or not candidate_answer.strip():
            unanswered_count += 1
            continue

        # 非客观题跳过
        if not is_objective_question(question_type):
            continue

        answered_count += 1

        # 评分
        score, is_correct = grade_question(
            question_type=question_type,
            candidate_answer=candidate_answer,
            standard_answer=standard_answer,
            full_score=full_score,
        )

        if is_correct:
            correct_count += 1
            total_score += score

    return total_score, answered_count, correct_count, unanswered_count
