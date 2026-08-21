# 【当前有效】AI评分机制说明

## ScoringAgent设计

### 类继承结构

```
BaseAgent (基类)
    │
    └── ScoringAgent (评分Agent)
            │
            ├── run()              // 主执行方法
            ├── validate_input()   // 输入校验
            ├── build_prompt()     // 构建Prompt
            ├── parse_response()   // 解析AI返回
            └── handle_error()     // 错误处理
```

### 核心方法说明

#### run() 方法
```python
def run(self, input_data: dict) -> dict:
    """
    主执行流程：
    1. validate_input()  → 校验输入
    2. build_prompt()    → 构建评分Prompt
    3. 调用LLM           → 发送请求到AI服务
    4. parse_response()  → 解析AI返回结果
    5. 返回结构化输出
    """
```

#### validate_input() 方法
```python
def validate_input(self, input_data: dict) -> bool:
    """
    校验输入完整性：
    - question.content 非空
    - standard_answer 非空
    - user_answer 非空
    - question.score > 0
    """
```

### 设计原则
- **单一职责**：仅负责评分逻辑
- **可插拔**：支持替换LLM提供商
- **可观测**：全链路日志记录
- **容错性**：完善的异常处理

---

## Prompt版本管理

### 版本列表

| 版本文件 | 类型 | 说明 |
|---------|------|------|
| `scoring/v1.yaml` | 评分 | 基础评分Prompt |
| `scoring/v2.yaml` | 评分 | 增强版评分Prompt |
| `scoring/v3.yaml` | 评分 | 最新评分Prompt（更精准的评分标准） |
| `report/v1.yaml` | 报告 | 报告生成Prompt |
| `analysis/v1.yaml` | 分析 | 分析报告Prompt |
| `agent/v1.yaml` | Agent | Agent系统Prompt |

### 版本演进说明

```
scoring/v1.yaml ──→ scoring/v2.yaml ──→ scoring/v3.yaml
   (基础版)              (增强版)           (最新版)
       
   - 简单对错判断        - 多维评分标准      - 精细化评分规则
   - 无理由说明          - 评分理由生成      - 分步骤评分
   - 无置信度            - 置信度计算        - 缺失要点识别
```

### v3.yaml（最新版）示例结构

```yaml
# scoring/v3.yaml
system_prompt: |
  你是一位专业的考试阅卷老师。请根据以下评分标准对考生的答案进行评分。
  
  评分标准：
  1. 完全正确：给满分
  2. 部分正确：根据正确程度给部分分数
  3. 完全错误：给0分
  4. 答案不完整但方向正确：适当给分

user_prompt: |
  题目：{question_content}
  参考答案：{standard_answer}
  考生答案：{user_answer}
  满分：{max_score}分
  
  请以JSON格式输出评分结果：
  {
    "score": <0-{max_score}>,
    "reason": "评分理由",
    "missing_points": ["缺失要点1", "缺失要点2"],
    "confidence": <0.0-1.0>
  }
```

---

## AI评分输入输出结构

### 输入结构

```typescript
interface AIScoringInput {
  question: {
    type: string;           // 题型标识
    content: string;       // 题目内容
    score: number;          // 题目满分
    options?: Option[];     // 选项（选择题）
  };
  standard_answer: string;  // 标准答案
  scoring_rules: string;    // 评分规则/要点（可选）
  user_answer: string;      // 用户作答
}
```

### 输入示例

```json
{
  "question": {
    "type": "short_answer",
    "content": "请简述公司的使命和愿景。",
    "score": 20
  },
  "standard_answer": "我们致力于用技术创新赋能每一位员工，让工作更高效、更有意义。",
  "scoring_rules": "回答需包含：1)技术创新 2)赋能员工 3)高效/有意义",
  "user_answer": "公司用技术让员工工作更高效。"
}
```

### 输出结构

```typescript
interface AIScoringOutput {
  score: number;                    // 得分（0至满分）
  reason: string;                   // 评分理由
  missing_points: string[];         // 缺失的要点
  confidence: number;                // AI置信度（0-1）
  model_used: string;               // 使用的模型名称
  prompt_version: string;           // 使用的Prompt版本
}
```

### 输出示例

```json
{
  "score": 12,
  "reason": "回答提到了'技术'和'高效'，但缺少'赋能员工'和'有意义'等核心要点，回答不够完整。",
  "missing_points": [
    "未明确提到'赋能员工'",
    "未提到'有意义'的层面"
  ],
  "confidence": 0.85,
  "model_used": "deepseek-chat",
  "prompt_version": "scoring/v3.yaml"
}
```

---

## AI报告输入输出结构

### 输入结构

```typescript
interface AIReportInput {
  exam_id: string;
  exam_title: string;
  candidate_name: string;
  results: Array<{
    question_id: string;
    question_content: string;
    question_type: string;
    score: number;
    max_score: number;
    user_answer: string;
    correct_answer: string;
    ai_comment?: string;
  }>;
  total_score: number;
  pass_score: number;
}
```

### 输出结构

```typescript
interface AIReportOutput {
  strengths: string[];          // 候选人优势
  weaknesses: string[];         // 候选人薄弱点
  learning_suggestions: string[]; // 学习建议
  overall_assessment: string;  // 综合评价
  model_used: string;
  prompt_version: string;
}
```

### 报告输出示例

```json
{
  "strengths": [
    "对公司核心价值观有较好的理解",
    "在技术相关题目中表现突出"
  ],
  "weaknesses": [
    "对公司历史和发展历程了解不足",
    "在多选题中容易遗漏选项"
  ],
  "learning_suggestions": [
    "建议阅读公司发展史相关资料",
    "加强对公司规章制度的学习",
    "练习多选题的答题技巧"
  ],
  "overall_assessment": "候选人在基础概念上表现良好，但在细节掌握和全面性上还有提升空间。建议加强对公司文化和历史的学习。",
  "model_used": "deepseek-chat",
  "prompt_version": "analysis/v1.yaml"
}
```

---

## DeepSeek接入

### 接口配置

```yaml
# AI服务配置
deepseek:
  api_base: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  model: "deepseek-chat"
  timeout: 30  # 秒
  max_retries: 2
```

### 接入方式

- **SDK**：兼容OpenAI SDK接口
- **调用方式**：`POST /chat/completions`
- **认证**：Bearer Token（API Key）

### 请求示例

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请评分以下答案..."}
    ],
    temperature=0.3,
    max_tokens=1000
)
```

### 错误处理策略

```
┌─────────────────────────────────────────────────────────────┐
│                      错误处理流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  请求发送                                                   │
│     │                                                       │
│     ▼                                                       │
│  ┌───────────┐                                             │
│  │ 成功返回   │                                             │
│  └─────┬─────┘                                             │
│        │ 失败                                               │
│        ▼                                                   │
│  ┌───────────┐                                             │
│  │ 重试(×2)  │ ──→ 成功 → 返回                              │
│  └─────┬─────┘                                             │
│        │ 仍然失败                                           │
│        ▼                                                   │
│  ┌───────────┐                                             │
│  │ 降级处理   │ ──→ 标记为"待人工批改"                      │
│  └─────┬─────┘                                             │
│        │                                                   │
│        ▼                                                   │
│  ┌───────────┐                                             │
│  │ 记录日志   │                                             │
│  └───────────┘                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 错误码处理

| HTTP状态码 | 处理方式 |
|-----------|---------|
| 429 | 限流，指数退避重试 |
| 400 | 参数错误，记录日志并返回 |
| 401/403 | 认证失败，告警通知 |
| 500/502/503 | 服务异常，重试后降级 |
| 超时 | 重试1次，仍超时则降级 |

---

## AI数据安全规则

### 数据分级

| 等级 | 数据类型 | 访问权限 |
|-----|---------|---------|
| **L1** | 公开数据（题目、选项） | 所有人可见 |
| **L2** | 候选人作答记录 | HR、候选人本人 |
| **L3** | AI评分结果与报告 | HR、候选人本人 |
| **L4** | API密钥、系统配置 | 仅系统管理员 |

### 脱敏访问

- **候选人姓名**：AI处理时使用匿名标识（Candidate_XXX）
- **手机号**：传输时脱敏（138****1234）
- **答案内容**：不包含任何个人身份信息
- **日志记录**：脱敏存储，不记录敏感原文

### 审计日志

所有AI调用均记录以下信息：

```json
{
  "timestamp": "2026-08-21T10:30:00Z",
  "request_id": "uuid-xxx",
  "agent": "ScoringAgent",
  "prompt_version": "scoring/v3.yaml",
  "model_used": "deepseek-chat",
  "input_summary": "题目ID: Q123, 题型: 简答题",
  "output_status": "success",
  "processing_time_ms": 2340,
  "operator": "system"
}
```

### 安全规则摘要

1. **数据最小化**：仅传评分必要字段，不传无关个人信息
2. **传输加密**：全链路HTTPS加密传输
3. **存储加密**：敏感字段数据库加密存储
4. **访问控制**：基于角色的严格权限管理
5. **日志审计**：所有AI调用可追溯、可审计
6. **数据隔离**：不同考试/候选人数据严格隔离
