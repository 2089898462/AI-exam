"""
评分规则Service
管理题目评分规则的增删改查
"""
from sqlalchemy.orm import Session

from app.exceptions import BusinessException, NotFoundException
from app.models.exam import Exam
from app.models.question_score_rule import QuestionScoreRule
from app.services.base import BaseService


class ScoreRuleService(BaseService[QuestionScoreRule]):
    """评分规则业务逻辑"""

    def __init__(self, db: Session):
        super().__init__(db, QuestionScoreRule)

    def create_rule(
        self,
        exam_id: int,
        question_type: str,
        score_method: str = "auto_compare",
        pass_score: float = 0,
        weight: float = 1.0,
        is_enabled: bool = True,
    ) -> QuestionScoreRule:
        """创建评分规则

        校验：
        - 考试必须存在
        - 题型必须有效
        - 同一考试同一题型只能有一条规则
        """
        # 检查考试存在
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        # 检查题型有效性
        valid_types = ["single_choice", "multiple_choice", "true_false", "short_answer"]
        if question_type not in valid_types:
            raise BusinessException(f"无效的题型: {question_type}")

        # 检查评分方法有效性
        valid_methods = ["auto_compare", "ai_score", "manual"]
        if score_method not in valid_methods:
            raise BusinessException(f"无效的评分方法: {score_method}")

        # 检查是否已存在
        existing = self.db.query(QuestionScoreRule).filter(
            QuestionScoreRule.exam_id == exam_id,
            QuestionScoreRule.question_type == question_type,
        ).first()
        if existing:
            raise BusinessException(f"该考试的 {question_type} 题型规则已存在")

        rule = QuestionScoreRule(
            exam_id=exam_id,
            question_type=question_type,
            score_method=score_method,
            pass_score=pass_score,
            weight=weight,
            is_enabled=is_enabled,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules_by_exam(self, exam_id: int) -> list[QuestionScoreRule]:
        """获取考试的所有评分规则"""
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundException("考试不存在")

        return self.db.query(QuestionScoreRule).filter(
            QuestionScoreRule.exam_id == exam_id
        ).order_by(QuestionScoreRule.question_type).all()

    def get_rule(self, rule_id: int) -> QuestionScoreRule:
        """获取单条评分规则"""
        rule = self.get(rule_id)
        if not rule:
            raise NotFoundException("评分规则不存在")
        return rule

    def update_rule(
        self,
        rule_id: int,
        score_method: str | None = None,
        pass_score: float | None = None,
        weight: float | None = None,
        is_enabled: bool | None = None,
    ) -> QuestionScoreRule:
        """更新评分规则"""
        rule = self.get_rule(rule_id)

        if score_method is not None:
            valid_methods = ["auto_compare", "ai_score", "manual"]
            if score_method not in valid_methods:
                raise BusinessException(f"无效的评分方法: {score_method}")
            rule.score_method = score_method

        if pass_score is not None:
            rule.pass_score = pass_score

        if weight is not None:
            rule.weight = weight

        if is_enabled is not None:
            rule.is_enabled = is_enabled

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> None:
        """删除评分规则"""
        rule = self.get_rule(rule_id)
        self.db.delete(rule)
        self.db.commit()

    def init_default_rules(self, exam_id: int) -> list[QuestionScoreRule]:
        """初始化默认评分规则

        为考试创建所有题型的默认规则：
        - 选择题（单选/多选/判断）：auto_compare，及格分 0，权重 1.0
        - 简答题：ai_score，及格分 0，权重 1.0
        
        如果某题型规则已存在，则跳过该题型。
        """
        default_rules = [
            {"question_type": "single_choice", "score_method": "auto_compare"},
            {"question_type": "multiple_choice", "score_method": "auto_compare"},
            {"question_type": "true_false", "score_method": "auto_compare"},
            {"question_type": "short_answer", "score_method": "ai_score"},
        ]

        created_rules = []
        for rule_data in default_rules:
            try:
                rule = self.create_rule(
                    exam_id=exam_id,
                    question_type=rule_data["question_type"],
                    score_method=rule_data["score_method"],
                    pass_score=0,
                    weight=1.0,
                    is_enabled=True,
                )
                created_rules.append(rule)
            except BusinessException:
                # 规则已存在，跳过
                pass

        return created_rules
