"""
知识库 Service
管理岗位、评分模板、评分规则的 CRUD 和版本控制
"""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.position import Position
from app.models.scoring_template import ScoringTemplate
from app.models.scoring_rule import ScoringRule


class KnowledgeBaseService:
    """知识库管理 Service"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 岗位管理 ====================

    def create_position(self, name: str, description: str | None = None) -> Position:
        """创建岗位"""
        existing = self.db.query(Position).filter(Position.name == name).first()
        if existing:
            raise ValueError(f"岗位 '{name}' 已存在")
        position = Position(name=name, description=description)
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def get_position(self, position_id: int) -> Position | None:
        """获取岗位"""
        return self.db.query(Position).filter(Position.id == position_id).first()

    def list_positions(self, is_active: bool | None = None) -> list[Position]:
        """列出岗位"""
        query = self.db.query(Position)
        if is_active is not None:
            query = query.filter(Position.is_active == is_active)
        return query.all()

    def update_position(self, position_id: int, name: str | None = None, description: str | None = None, is_active: bool | None = None) -> Position:
        """更新岗位"""
        position = self.get_position(position_id)
        if not position:
            raise ValueError(f"岗位 {position_id} 不存在")
        if name is not None:
            existing = self.db.query(Position).filter(Position.name == name, Position.id != position_id).first()
            if existing:
                raise ValueError(f"岗位名称 '{name}' 已存在")
            position.name = name
        if description is not None:
            position.description = description
        if is_active is not None:
            position.is_active = is_active
        self.db.commit()
        self.db.refresh(position)
        return position

    def delete_position(self, position_id: int) -> None:
        """删除岗位（软删除）"""
        position = self.get_position(position_id)
        if not position:
            raise ValueError(f"岗位 {position_id} 不存在")
        # 检查是否有关联模板
        template_count = self.db.query(ScoringTemplate).filter(ScoringTemplate.position_id == position_id, ScoringTemplate.is_active == True).count()
        if template_count > 0:
            raise ValueError(f"岗位 {position_id} 有关联的激活模板，无法删除")
        position.is_active = False
        self.db.commit()

    # ==================== 评分模板管理 ====================

    def create_template(self, position_id: int, name: str, description: str | None = None) -> ScoringTemplate:
        """创建评分模板"""
        position = self.get_position(position_id)
        if not position:
            raise ValueError(f"岗位 {position_id} 不存在")
        template = ScoringTemplate(position_id=position_id, name=name, description=description)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template(self, template_id: int) -> ScoringTemplate | None:
        """获取模板"""
        return self.db.query(ScoringTemplate).filter(ScoringTemplate.id == template_id).first()

    def list_templates(self, position_id: int | None = None, is_active: bool | None = None) -> list[ScoringTemplate]:
        """列出模板"""
        query = self.db.query(ScoringTemplate)
        if position_id is not None:
            query = query.filter(ScoringTemplate.position_id == position_id)
        if is_active is not None:
            query = query.filter(ScoringTemplate.is_active == is_active)
        return query.all()

    def update_template(self, template_id: int, name: str | None = None, description: str | None = None, is_active: bool | None = None) -> ScoringTemplate:
        """更新模板"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if is_active is not None:
            template.is_active = is_active
        self.db.commit()
        self.db.refresh(template)
        return template

    # ==================== 评分规则管理 ====================

    def create_rule(
        self,
        template_id: int,
        rule_name: str,
        content: str,
        rule_type: str = "knowledge_point",
        key_points: str | None = None,
        deduction_rules: str | None = None,
        weight: float = 1.0,
    ) -> ScoringRule:
        """创建评分规则"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        # 获取当前最大版本号
        max_version = self.db.query(ScoringRule.version).filter(ScoringRule.template_id == template_id).order_by(ScoringRule.version.desc()).first()
        next_version = (max_version[0] if max_version else 0) + 1
        rule = ScoringRule(
            template_id=template_id,
            version=next_version,
            rule_name=rule_name,
            rule_type=rule_type,
            content=content,
            key_points=key_points,
            deduction_rules=deduction_rules,
            weight=weight,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rule(self, rule_id: int) -> ScoringRule | None:
        """获取规则"""
        return self.db.query(ScoringRule).filter(ScoringRule.id == rule_id).first()

    def list_rules(self, template_id: int | None = None, is_active: bool | None = None) -> list[ScoringRule]:
        """列出规则"""
        query = self.db.query(ScoringRule)
        if template_id is not None:
            query = query.filter(ScoringRule.template_id == template_id)
        if is_active is not None:
            query = query.filter(ScoringRule.is_active == is_active)
        return query.order_by(ScoringRule.version).all()

    def update_rule(
        self,
        rule_id: int,
        rule_name: str | None = None,
        content: str | None = None,
        key_points: str | None = None,
        deduction_rules: str | None = None,
        weight: float | None = None,
        is_active: bool | None = None,
    ) -> ScoringRule:
        """更新规则（创建新版本）"""
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"规则 {rule_id} 不存在")
        # 创建新版本
        new_version = rule.version + 1
        new_rule = ScoringRule(
            template_id=rule.template_id,
            version=new_version,
            rule_name=rule_name or rule.rule_name,
            rule_type=rule.rule_type,
            content=content or rule.content,
            key_points=key_points if key_points is not None else rule.key_points,
            deduction_rules=deduction_rules if deduction_rules is not None else rule.deduction_rules,
            weight=weight if weight is not None else rule.weight,
        )
        # 旧版本标记为不活跃
        rule.is_active = False
        self.db.add(new_rule)
        self.db.commit()
        self.db.refresh(new_rule)
        return new_rule

    def get_latest_rules(self, template_id: int) -> list[ScoringRule]:
        """获取模板的最新激活规则"""
        return self.db.query(ScoringRule).filter(
            ScoringRule.template_id == template_id,
            ScoringRule.is_active == True,
        ).order_by(ScoringRule.version.desc()).all()

    # ==================== RAG 检索 ====================

    def retrieve_scoring_context(self, position_id: int | None = None, template_id: int | None = None) -> dict[str, Any]:
        """
        检索评分上下文（RAG）
        返回用于 AI 评分的结构化评分标准
        """
        result = {
            "position": None,
            "template": None,
            "rules": [],
            "rule_versions": [],
        }

        # 获取岗位信息
        if position_id:
            position = self.get_position(position_id)
            if position:
                result["position"] = {
                    "id": position.id,
                    "name": position.name,
                    "description": position.description,
                }

        # 获取模板和规则
        if template_id:
            template = self.get_template(template_id)
            if template:
                result["template"] = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                }
                rules = self.get_latest_rules(template_id)
                for rule in rules:
                    rule_data = {
                        "id": rule.id,
                        "version": rule.version,
                        "rule_name": rule.rule_name,
                        "rule_type": rule.rule_type,
                        "content": rule.content,
                        "key_points": rule.key_points,
                        "deduction_rules": rule.deduction_rules,
                        "weight": rule.weight,
                    }
                    result["rules"].append(rule_data)
                    result["rule_versions"].append({
                        "rule_id": rule.id,
                        "version": rule.version,
                    })

        return result

    def find_template_by_position(self, position_id: int) -> ScoringTemplate | None:
        """根据岗位查找激活的模板"""
        return self.db.query(ScoringTemplate).filter(
            ScoringTemplate.position_id == position_id,
            ScoringTemplate.is_active == True,
        ).first()

    def format_rules_for_prompt(self, rules: list[dict]) -> str:
        """将规则格式化为 Prompt 可用的文本"""
        if not rules:
            return "暂无评分标准规则"

        parts = []
        for i, rule in enumerate(rules, 1):
            part = f"### 规则 {i}: {rule.get('rule_name', '未命名')} (权重: {rule.get('weight', 1.0)})\n"
            part += f"**评分内容**: {rule.get('content', '')}\n"
            if rule.get('key_points'):
                part += f"**关键知识点**: {rule['key_points']}\n"
            if rule.get('deduction_rules'):
                part += f"**扣分规则**: {rule['deduction_rules']}\n"
            parts.append(part)

        return "\n".join(parts)
