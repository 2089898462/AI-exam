# 测试计划

## 测试阶段
- 单元测试：各模块独立测试
- 集成测试：模块间交互测试
- AI 评估测试：Prompt 效果验证

## 测试目录
```
tests/
├── backend/    # 后端 API 测试
├── ai/         # AI 服务测试
└── frontend/   # 前端组件测试（待定）
```

## AI 评估
- 测试用例：`ai-service/app/evaluation/`
- 评分准确性验证
- 报告质量验证