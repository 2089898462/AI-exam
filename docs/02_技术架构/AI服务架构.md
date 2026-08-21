# AI 服务架构设计

> **【当前有效】**
> 版本：v1.0  
> 更新时间：2026-08-21

---

## 1. AI 服务架构图

```
┌─────────────────────────────────────────────────────────┐
│                      Agent 层                             │
│   ScoringAgent / ReportAgent / ConversationAgent          │
│                  ▲                                        │
│                  │ 继承                                   │
│            BaseAgent                                     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    LLM Client 层                          │
│   client / models / provider                              │
│   - 统一封装大模型调用，支持多模型切换                      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Prompt 模板管理                            │
│   scoring/v1~v3、report/v1、analysis/v1、agent/v1         │
│   - YAML 版本化管理，可灰度发布                           │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              外部 LLM（DeepSeek 等）                      │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Agent 体系

### 2.1 Agent 列表

| Agent | 职责 | 关键特性 |
|-------|------|---------|
| **ScoringAgent** | 主观题评分 | Prompt 多版本（v1~v3），支持按题目类型调度 |
| **ReportAgent** | 考试分析报告 | 聚合多场考试结果，生成结构化报告 |
| **ConversationAgent** | 对话交互 | 候选人问答、学习建议、上下文多轮 |
| **BaseAgent** | 基础 Agent 类 | `run()` / `validate_input()` 通用能力 |

### 2.2 Agent 运行机制
1. 继承 `BaseAgent`，实现 `run(input)` 方法
2. 在 `run()` 内调用 `validate_input()` 校验输入
3. 通过 LLM Client 加载 Prompt 模板
4. 组装 Prompt → 调用 LLM → 解析结构化输出
5. 返回统一的 `AgentResult`（包含 content、raw、metadata）

---

## 3. AI 服务目录结构

```
ai-service/
├── app/
│   ├── agents/              # Agent 定义（ScoringAgent/ReportAgent/ConversationAgent/BaseAgent）
│   ├── llm/                 # LLM 客户端（client、models、provider）
│   ├── prompts/            # Prompt 模板
│   │   ├── scoring/v1/ ~ v3/
│   │   ├── report/v1/
│   │   ├── analysis/v1/
│   │   └── agent/v1/
│   ├── tools/               # AI 工具（exam_tools、tool_registry）
│   ├── api/endpoints/       # API 端点（scoring、report、agent、health）
│   └── schemas/             # 数据校验（Pydantic）
```

### 3.1 目录职责说明

| 目录 | 职责 |
|------|------|
| `ai-service/app/agents/` | Agent 定义，业务逻辑封装 |
| `ai-service/app/llm/` | LLM 客户端：client、models、provider 抽象层 |
| `ai-service/app/prompts/` | Prompt 模板，按 Agent + 版本组织 |
| `ai-service/app/tools/` | AI 工具：exam_tools、tool_registry |
| `ai-service/app/api/endpoints/` | API 端点：scoring、report、agent、health |
| `ai-service/app/schemas/` | Pydantic 数据校验模型 |

---

## 4. AI 调用流程

```
Backend
  │
  │ 1. HTTP POST /api/v1/scoring { exam_id, answers, ... }
  ▼
AI Service
  │
  │ 2. 根据 endpoint 路由到对应 Agent
  ▼
Agent.run(input)
  │
  │ 3. validate_input() 校验
  │ 4. 加载 Prompt 模板（按版本号）
  │ 5. 组装 messages
  ▼
LLM Client
  │
  │ 6. 调用 provider（DeepSeek）
  ▼
DeepSeek API
  │
  │ 7. 返回结构化 JSON
  ▼
Agent 解析结果
  │
  │ 8. 填充 AgentResult
  ▼
AI Service 返回结构化响应
  │
  │ 9. Backend 解析并落库
  ▼
MySQL（ai_score_record / ai_report）
```

---

## 5. Prompt 版本管理规则

1. **YAML 文件**：所有 Prompt 以 `.yaml` 文件存储，便于审计与 Diff。
2. **按版本号命名**：`prompts/scoring/v1/prompt.yaml`、`v2/prompt.yaml`、`v3/prompt.yaml`。
3. **修改即升级**：调整 Prompt 时创建新版本，禁止覆盖历史版本。
4. **版本可切换**：Backend 调用时可指定 Prompt 版本，支持灰度。
5. **版本备案**：每次新版本需在 `prompt-version.md` 中记录变更说明。

### 5.1 Prompt 目录示例
```
prompts/
├── scoring/
│   ├── v1/prompt.yaml    # 初始版
│   ├── v2/prompt.yaml    # 优化版（更细粒度评分）
│   └── v3/prompt.yaml    # 最新版（支持多维度评分）
├── report/v1/prompt.yaml
├── analysis/v1/prompt.yaml
└── agent/v1/prompt.yaml
```

---

## 6. 数据安全访问规则

### 6.1 数据分级
| 级别 | 类型 | 访问规则 |
|------|------|---------|
| **L1** | 公开/匿名数据 | AI 可直接读取（如题库） |
| **L2** | 候选人敏感数据 | 必须脱敏后再传入 AI（如姓名、手机号、邮箱） |
| **L3** | HR/管理员操作数据 | AI 禁止访问 |
| **L4** | 系统配置/密钥 | AI 禁止访问 |

### 6.2 安全规范
- **AI 服务禁止直接访问数据库**：所有数据必须由 Backend 脱敏后通过 HTTP 传入。
- **L2 数据脱敏规则**：姓名保留首字、手机号中间四位打码、邮箱域名保留。
- **日志审计**：每次 AI 调用必须记录 `ai_call_log`，包含输入摘要、token 消耗、耗时。
- **超时与降级**：AI 调用超时设置为 10 秒，失败后降级为规则评分。
