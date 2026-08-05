# AI Agent 设计

## 架构

```
┌─────────────────────────────────────┐
│           AI Service                │
│                                     │
│  ┌─────────────┐  ┌─────────────┐  │
│  │ 评分 Agent  │  │ 报告 Agent  │  │
│  └──────┬──────┘  └──────┬──────┘  │
│         │                │         │
│         ▼                ▼         │
│  ┌─────────────────────────────┐   │
│  │        LLM Client           │   │
│  │    (OpenAI 兼容接口)         │   │
│  └─────────────┬───────────────┘   │
│                │                   │
│         Prompt 模板管理             │
│  ┌─────────────┬───────────────┐   │
│  │ scoring/v1  │  report/v1    │   │
│  └─────────────┴───────────────┘   │
└─────────────────────────────────────┘
```

## Agent 定义

### 评分 Agent
- 输入：题目、标准答案、评分规则、用户答案
- 输出：{score, reason, missing_points, confidence}
- Prompt 版本：prompts/scoring/v1.yaml

### 报告 Agent
- 输入：考试结果数据
- 输出：{strengths, weaknesses, learning_suggestions}
- Prompt 版本：prompts/report/v1.yaml

## Prompt 管理规范
- 所有 Prompt 为 YAML 文件
- 按版本号管理（v1, v2...）
- 与业务代码完全分离
- 支持版本回退