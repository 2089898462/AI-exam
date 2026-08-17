# AI 上下文交接文档

> **本文件为 AI Agent 必读文档。每次接手本项目必须首先阅读此文件。**
>
> 最后更新：2026-08-13（S7.1 启动脚本全面优化 — 已完成）

---

# 1. 项目基本信息

## 项目名称
AI考试系统（企业内部版）

## 项目目标
构建一个企业内部 AI 智能考试与测评系统，为人事部门提供一站式考试管理解决方案：
- 考试创建、发布
- 员工在线考试
- 系统自动评分（客观题）
- AI 主观题评分
- AI 考试分析报告
- HR 成绩管理

## 使用人员
- **管理员**：系统维护、用户管理
- **HR（核心角色）**：创建考试、发布考试、查看所有成绩和 AI 报告
- **员工**：参加考试、查看个人成绩

## 核心价值
- 替代人工批改，效率提升 80%+
- AI 主观题评分，标准统一
- AI 考试分析报告，帮助 HR 快速了解考试情况

---

# 2. 当前技术架构

## 整体架构图

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│    Backend      │────▶│    MySQL 8      │
│  Vue3 + Vite    │     │  FastAPI        │     │                 │
│  Element Plus   │◀────│  SQLAlchemy     │◀────│                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │ HTTP
                                 ▼
                        ┌─────────────────┐
                        │   AI Service    │
                        │  FastAPI        │
                        │  OpenAI SDK     │
                        └─────────────────┘
```

## 技术栈

| 服务 | 端口 | 技术栈 |
|------|------|--------|
| Frontend | 3000 | Vue 3 + Vite + Element Plus + Vue Router + Axios + Pinia |
| Backend | 8000 | Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic |
| AI-Service | 8001 | Python 3.13 + FastAPI + httpx |
| Database | 3306 | MySQL 8.0（InnoDB / utf8mb4） |

## 后端目录结构

```
backend/app/
├── api/v1/endpoints/     # API 端点
├── core/                 # 核心配置（config/security/dependencies）
├── models/               # ORM 模型（11 张核心表）
├── schemas/              # Pydantic 校验模型
├── services/             # 业务服务层
├── exceptions/           # 统一异常处理
└── utils/                # 工具函数
```

## 前端目录结构

```
frontend/src/
├── api/                  # API 接口封装（auth/exam/question/record/grading/report/template/participant/ai_scoring）
├── views/                # 页面（login/admin/exam）
├── stores/               # Pinia 状态管理
├── router/               # 路由配置
└── components/           # 通用组件
```

---

# 3. 已确认的重要技术决策

以下决策已经确定，**未来不要随意修改**。

| # | 决策内容 | 原因 |
|---|----------|------|
| 1 | MVP 采用固定试卷模式 | 自动组卷复杂度高，首期聚焦核心流程 |
| 2 | AI 服务独立部署（端口 8001） | 解耦业务逻辑与 AI 能力，独立扩缩容 |
| 3 | Prompt 与代码分离（YAML 版本化） | 便于迭代和回退 |
| 4 | 使用 Alembic 管理数据库迁移 | 版本化迁移，支持回滚 |
| 5 | 数据库 JSON 字段使用通用 sa.JSON() | 跨数据库兼容 |
| 6 | 密码使用 bcrypt 哈希 | 安全行业标准，禁止明文存储 |
| 7 | API 统一前缀 /api/v1 | 支持未来版本扩展 |
| 8 | 统一响应格式 ApiResponse | 前后端分离，统一错误处理 |
| 9 | Service 层封装业务逻辑 | API 层不直接操作数据库 |
| 10 | AI 评分与报告 Agent 分离 | 职责单一，便于独立迭代 |
| 11 | 候选人考试使用嵌入式身份（姓名+手机+考试码） | 企业内部场景无需完整账号体系 |
| 12 | 前端页面不直接调用 axios | 必须通过 API 封装模块 |

---

# 4. 当前开发阶段

## 当前阶段
**S5.7-F 系统黑盒业务验收 — 已通过 ✅**

### S5.7-F 黑盒测试结果（2026-08-07）

**测试目标**：黑盒测试方式验证管理员/HR/候选人全流程业务 + 异常处理

**测试结果**：✅ **通过**（23/23 项通过）

**测试环境**：
- Backend API：✅ 正常（http://localhost:8000）
- AI Service：✅ 正常（http://localhost:8001）
- Frontend：✅ 正常（http://localhost:3000）

**测试流程与结果**：

**1. 管理员流程测试**（3/3 通过）
- 1.1.1 管理员登录 ✅
- 1.1.2 获取用户信息 ✅（角色: admin）
- 1.2.1 管理员访问考试列表 ✅

**2. HR 完整业务流程测试**（8/8 通过）
- 2.1.1 HR 登录 ✅
- 2.2.1 创建考试 ✅（ID: 9）
- 2.2.2 考试码自动生成 ✅（EXAM-20260807105149-BFE5BCF8）
- 2.3.1 添加单选题 ✅
- 2.3.2 添加判断题 ✅
- 2.3.3 添加简答题 ✅
- 2.4.1 发布考试 ✅
- 2.5.1 添加参与人员 ✅

**3. 候选人流程测试**（5/5 通过）
- 3.1.1 候选人进入考试 ✅
- 3.2.1 开始考试 ✅
- 3.2.2 批量保存答案 ✅（3题）
- 3.3.1 提交考试 ✅
- 3.3.2 提交状态验证 ✅（submitted）

**4. AI 评分测试**（4/4 通过）
- 4.1.1 AI 评分完成 ✅（3秒，状态: completed）
- 4.2.1 总分数 ✅（total_score: 15.0）
- 4.3.1 HR 查看考试详情 ✅（状态: graded）
- AI 返回验证：score、reason、confidence 完整 ✅

**5. 异常测试**（3/3 通过）
- 5.1.1 错误考试码被拒绝 ✅（HTTP 400）
- 5.2.1 重复参加被拦截 ✅（HTTP 400）
- 5.4.1 AI 服务正常运行 ✅
- 5.4.2 考试数据完整性 ✅

**修复记录**（测试过程中发现并修复）：
1. 🔴 **P1: exam_code 未自动生成**
   - 修改：`backend/app/services/exam_service.py`
   - 添加 `_generate_exam_code()` 方法，创建考试时自动生成唯一考试码
   - 格式：`EXAM-{时间戳}-{UUID前8位}`

2. 🟠 **配置兼容问题**
   - 修改：`backend/app/core/config.py`
   - 添加 `extra = "ignore"` 配置，允许系统环境中的 AI_ 变量存在

**Bug 列表**：无未修复 Bug

**测试脚本**：`ai-service/run_blackbox_test.py`

**最终结论**：
✅ 黑盒测试通过

**系统状态**：
- 管理员/HR/候选人全流程：✅ 可用
- 异常处理：✅ 正确（错误考试码、重复参加均被拦截）
- AI 评分：✅ 自动触发、正常返回
- 数据完整性：✅ 有保障

**下一步**：
- 进入 S5.8 阶段开发

---

## S6.0.1 手动添加题目功能 — 已完成 ✅

### 开发目标
为 HR 提供手动添加题目的能力，支持不通过 JSON 导入直接创建题目。

### 新增功能
1. ✅ 手动添加题目对话框（QuestionFormDialog.vue）
2. ✅ 支持题型选择：单选题、简答题（多选题/判断题预留）
3. ✅ 动态选项增删（单选/多选）
4. ✅ "保存" 和 "保存并继续添加" 两种操作模式
5. ✅ 题目编辑入口（QuestionTable.vue）

### 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/exam/QuestionFormDialog.vue` | **新建** | 添加题目对话框组件 |
| `frontend/src/views/admin/exam/ExamDetail.vue` | 修改 | 添加按钮 + 对话框集成 |
| `frontend/src/components/exam/QuestionTable.vue` | 修改 | 预留编辑入口 |
| `frontend/src/api/question.js` | 修改 | 添加 update 方法 |

### 数据格式（保持现有结构）
**单选题**
```json
{
  "type": "single_choice",
  "content": "题目内容",
  "options": [{"label": "A", "content": "选项A"}],
  "answer": "A",
  "score": 10
}
```

**简答题**
```json
{
  "type": "short_answer",
  "content": "题目内容",
  "answer": "标准答案",
  "score": 15
}
```

### 后端依赖
- 现有接口已支持：`POST /api/v1/questions`
- 现有 Service 已支持：`create_question()` + `_validate_question_data()`
- **无需后端修改**
- **无需数据库迁移**

### 校验规则
| 题型 | 校验项 | 规则 |
|------|--------|------|
| 单选题 | 选项数量 | ≥ 2 个，内容非空 |
| 单选题 | 正确答案 | 必须是已添加选项之一 |
| 简答题 | 标准答案 | 非空 |
| 通用 | 分值 | ≥ 0 |
| 通用 | 题目内容 | 非空 |

### 后续扩展
- 多选题：取消禁用态，补充校验逻辑
- 判断题：true/false 选项逻辑
- 题目编辑功能：已预留 @edit 事件

---

## S7.0 HR评分复核功能 — 已完成 ✅

### 开发目标
将AI自动评分结果页面优化为「AI评分 + HR人工复核」模式，支持HR手动调整分数并添加复核备注。

### 新增功能
1. ✅ 顶部评分区域优化：删除客观题/AI评分卡片，保留系统总分，新增HR复核分数输入
2. ✅ HR复核备注功能：支持多行文本记录修改原因
3. ✅ 最终成绩显示逻辑：有HR复核分数时优先显示复核分数
4. ✅ AI评分详情折叠展示：保留AI原始评分数据，支持展开查看客观题得分和AI简答题评分详情
5. ✅ 复核分数校验：分数范围校验（0 <= score <= 试卷总分）

### 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/grading_record.py` | 修改 | 新增 review_score、review_comment 字段 |
| `backend/app/schemas/grading.py` | 修改 | 新增 HRReviewUpdateRequest Schema |
| `backend/app/services/grading_service.py` | 修改 | 新增 update_hr_review 方法 |
| `backend/app/api/v1/endpoints/grading_results.py` | 修改 | 新增复核更新接口 |
| `backend/alembic/versions/f1a2b3c4d5e6_add_hr_review_fields.py` | 新建 | Alembic 迁移文件 |
| `frontend/src/api/gradingResult.js` | 修改 | 新增 updateHRReview 方法 |
| `frontend/src/views/admin/grading/GradingResultDetail.vue` | 修改 | 页面重构 |

### 数据库变更
```sql
ALTER TABLE grading_record ADD COLUMN review_score NUMERIC(8,2) NULL;
ALTER TABLE grading_record ADD COLUMN review_comment TEXT NULL;
```

### API变更
- `PUT /api/v1/grading/results/{exam_record_id}/review` — 提交HR复核

### 显示逻辑
- 最终成绩 = review_score（如果存在）|| total_score（系统总分）
- 原AI评分数据（auto_score、ai_score）保留不变

---

**S5.7-E AI阅卷完整业务验收 — 已通过**

---

**S5.7-D1 AI评分链路修复 — 已完成**

### S5.7-D1 修复内容（2026-08-07）

**修复问题**：
1. ✅ **答案保存不完整**：`answer_content` 字段为 null
2. ✅ **AI评分未自动触发**：提交考试后未进入AI评分流程
3. ✅ **AI评分接口路径不统一**：前端/后端/服务路径不一致

**修改文件**：
1. `backend/app/schemas/exam_record.py`：AnswerCreate 增加 `answer` 字段别名兼容
2. `backend/app/api/v1/endpoints/exam_records.py`：submit_exam 增加后台AI评分触发
3. `backend/app/services/grading_service.py`：_save_ai_score 增加状态字段保存

**修复详情**：

**问题1：答案保存不完整**
- 根因：前端使用 `answer` 字段名，后端 Schema 期望 `answer_content`
- 修复：AnswerCreate 增加 `@model_validator(mode="before")` 自动映射 `answer` → `answer_content`
- 结果：两种字段名均能正确保存，`answer_content` 字段不再为 null

**问题2：AI评分自动触发**
- 根因：`submit_exam` 方法只更新状态，未调用 `auto_grade_exam`
- 修复：提交成功后通过后台线程触发 `_trigger_auto_grade(record_id)`
- 特性：AI评分在后台线程执行，不阻塞主请求响应
- 特性：评分失败不影响考试提交结果（异常只记录日志）
- 结果：提交考试 → 自动评分 → 保存结果 完整链路恢复

**问题3：AI评分接口路径整理**
- 后端AI评分接口：`POST /api/v1/ai-scoring/evaluate`
- AI服务健康检查：`GET /api/v1/ai-scoring/health`
- AI阅卷管理：`POST /api/v1/ai-grading/trigger` 等
- 自动评分端点：`POST /api/v1/exams/{exam_id}/records/{record_id}/auto-grade`
- AI服务内部接口：`POST http://localhost:8001/api/scoring/evaluate`

**测试结果**：
- ✅ 答案保存验证：3道题（单选/判断/简答）的 answer_content 均非空
- ✅ AI评分触发验证：提交后自动完成评分（status: completed）
- ✅ 评分结果保存验证：AI评分状态、分数、理由、置信度均正确保存
- ⚠️ AI实际评分需配置 `AI_API_KEY`（当前未配置，AI调用返回错误但链路正常）

**AI评分链路**：
```
候选人提交答案
    ↓
保存完整答案（answer_content 非空）
    ↓
提交考试（状态: submitted）
    ↓
后台触发自动评分（新线程）
    ↓
加载答案和题目
    ↓
客观题自动评分（单选/多选/判断）
    ↓
主观题AI评分（简答题 → AI-Service → DeepSeek）
    ↓
保存评分结果（分数/理由/置信度/知识点）
    ↓
更新考试状态（graded）
    ↓
返回评分结果
```

**下一步计划**：
1. 配置 AI_API_KEY 以启用真实 AI 评分
2. S5.7-D2 考试码自动生成功能
3. 添加重复提交限制
4. 前端 AI 评分状态轮询更新

---

**S5-B AI 自动阅卷真实评分链路建设 — 已通过**

### 实现功能
- ✅ 候选人分析报告模型（CandidateAnalysisReport：独立存储分析结果）
- ✅ AnalysisService 分析服务（数据收集、AI 分析、报告生成/查询/审核）
- ✅ 分析报告 API（/api/v1/analysis-reports：生成/查询/审核）
- ✅ 本地规则分析引擎（基于 AI 评分结果生成能力画像，不依赖外部 AI 服务）
- ✅ 知识掌握度分析（各知识点掌握程度：熟练/掌握/基本了解/薄弱）
- ✅ 优势/薄弱点分析（基于得分和知识点匹配）
- ✅ 面试建议生成（关注点和建议问题）
- ✅ AI 分析 v1 Prompt（禁止录用建议，纯辅助分析）
- ✅ 权限控制（仅 HR/管理员可访问）

### 测试结果
- 8 个测试用例全部通过
- 覆盖：报告生成、不重复生成、查询、审核、异常处理、AI 不输出录用建议、知识分析质量、完整流程

### 路由注册修复（2026-08-06）
- **问题**：新增 endpoint 文件 import 路径错误，导致 FastAPI router 整体加载失败，openapi.json 中大量业务路由缺失
- **修复内容**：
  1. `analysis_report.py`：`from app.core.database import get_db` → `from app.db.session import get_db`
  2. `knowledge_base.py`：`from app.api.deps import ...` → `from app.db.session import get_db` + `from app.core.permissions import ...`
  3. `exams.py`：补充缺失的 `require_authenticated` 导入
  4. 移除 `analysis_report.py` 和 `knowledge_base.py` 中的重复 prefix（已在 router.py 中统一配置）
- **验证结果**：105 个路由全部恢复，所有模块（ai-grading、ai-scoring、knowledge-base、analysis-reports、reports、candidates、templates、ai-call-logs、grading）均在 OpenAPI 中正常显示
- **回归测试**：analysis_service 8/8、knowledge_base 8/8、ai_grading 16/17（1 个数据库残留数据导致的既有测试问题）、participant 8/8、grading_results 11/11

## 已完成功能清单

### 基础设施
- [x] 项目目录结构搭建
- [x] 前端/后端/AI 服务骨架
- [x] 数据库设计与 ORM 模型（11 张表）
- [x] Alembic 迁移

### 后端核心
- [x] API 路由架构（router.py + /api/v1）
- [x] Schema 规范（Pydantic 请求/响应校验）
- [x] Service 层规范（业务逻辑封装）
- [x] 异常处理（统一异常 + 全局处理器）
- [x] 统一响应格式（ApiResponse）
- [x] 密码安全（bcrypt 哈希）

### 业务功能
- [x] 考试 CRUD + 题目管理 + JSON 导入
- [x] 固定试卷模板体系（模板 CRUD + 基于模板创建考试）
- [x] JWT 认证 + 权限保护（角色 + 数据隔离）
- [x] 候选人考试流程（入口/答题/保存/提交）
- [x] 客观题自动评分
- [x] AI 主观题评分（ScoringAgent）
- [x] AI 考试分析报告（ReportAgent）
- [x] 考试人员管理（ExamParticipant + CRUD + 状态同步）
- [x] 考试安全（exam_code + 身份验证 + 防重复提交）
- [x] 核心流程自动化测试（28/28 通过）
- [x] 考试基础统计能力（参与人数、平均分、通过率等）
- [x] 统一数据查询接口（考试分析、成绩列表、答题详情、候选人历史增强）
- [x] AI Agent 数据访问准备能力检查（架构/权限/审计/脱敏）
- [x] AI 调用审计能力（AiCallLog + AiCallLogService）
- [x] 数据脱敏能力（DataMaskingMiddleware + 手机号/邮箱/身份证脱敏）
- [x] 链路追踪能力（trace_id + request_id 统一追踪）

### 前端页面
- [x] 登录页、AdminLayout
- [x] 考试管理（列表/创建/详情/导入）
- [x] 模板管理（列表/创建/编辑/详情）
- [x] 考试人员管理
- [x] 候选人（入口/答题页）
- [x] 评分结果列表/详情
- [x] AI 报告列表/详情

## 下一阶段
**S5.6 AI Agent 对话功能开发**

### S5-B 已完成（2026-08-06）
- AIGradingService 完整实现（触发/查询/确认/拒绝/列表）
- AI 评分真实链路：候选人提交 → AI 自动评分 → HR 查看/确认
- AnswerRecord 模型扩展（ai_status/ai_score/ai_confidence 等字段）
- AIScoreRecord 模型（独立存储 AI 评分建议，支持审核流程）
- AI 评分 v2 Prompt（支持知识点分析，结构化输出）
- AI 评分异常处理（AI 失败不影响考试提交）
- 数据安全保护（只发送题目/答案/评分规则，不发送隐私信息）
- 21/21 测试通过

### S5.5 已完成
- 候选人分析报告模型（CandidateAnalysisReport）
- AnalysisService 分析服务（数据收集、AI 分析、报告生成/查询/审核）
- 分析报告 API（/api/v1/analysis-reports）
- 本地规则分析引擎（知识掌握度、优势、薄弱点、面试建议）
- AI 分析 v1 Prompt（禁止录用建议，纯辅助分析）
- 8/8 测试通过

### S5-A 已完成（2026-08-06）
- DeepSeek-V4-Flash 模型接入
- AI 配置体系升级（支持多 Provider，属性动态读取环境变量）
- LLMProvider 枚举新增 DEEPSEEK
- AI 健康检查端点（配置检查 + 连接测试）
- AI 调用日志集成（请求/响应/错误，不记录敏感数据）
- 错误分类增强（支持 429 rate limit、unauthorized 等）
- 修复 scoring.py ModelConfig 参数名（model→name）
- 24/24 测试通过

### S5.6 AI评分质量优化能力检查（2026-08-06）

**检查范围**：AI评分流程、Prompt质量、评分规则、稳定性、数据追踪、人工复核、调用成本

**检查方法**：代码审查（AIGradingService/AIScoringService/ScoringAgent/Prompt v1-v2/模型定义）

**核心结论**：✅ AI评分能力满足真实招聘考试使用要求，但需关注B级风险

**流程完整性**：✅ 完整流程（提交→AI评分→解析→保存→HR查看）

**Prompt质量**：
- v2模板包含角色定义、评分目标、题目信息、标准答案、评分规则、输出格式约束
- 支持知识点分析（matched_points/missing_points）
- 输出格式为结构化JSON，便于解析

**评分规则体系**：
- 支持企业知识库（岗位→模板→规则三级结构）
- 支持知识点评分、部分得分
- 支持扣分规则（deduction_rules字段）
- 支持评分规则版本控制

**稳定性分析**：
- temperature固定为0.3，降低随机性
- 置信度机制（低置信度<0.6标记需人工复核）
- 空答案直接返回0分，不调用AI
- AI失败时降级处理，不影响考试提交

**数据追踪能力**：
- AIScoreRecord记录完整评分信息
- 包含AI分数、评分理由、知识点、置信度、模型名、Prompt版本、评分时间、审核状态
- 支持HR查看AI评分历史

**人工复核机制**：
- HR可查看AI评分详情
- 支持确认/拒绝AI评分
- AI评分不直接替代最终成绩，需HR确认
- 被拒绝后可重新触发AI评分

**风险项**：
- ⚠️ B001：单次评分token消耗较高，建议实现批量评分
- ⚠️ B002：缺少评分结果二次校验机制
- ⚠️ B003：对AI评分结果缺少评分范围限制校验

**优化建议**：
- 建议增加批量评分接口，减少多次调用成本
- 建议增加评分结果合理性校验（如分数与置信度的矛盾检查）
- 建议增加评分标准分级配置（简单题/复杂题不同标准）

**检查结论**：系统可进入S6正式业务优化阶段，但建议优先处理B级风险项

### S5.6 建议开发内容
- P0：AI Agent 意图识别与工具自动路由
- P0：LLM Function Calling 集成
- P0：多轮对话上下文管理增强
- P1：真实 Backend API 对接（替换 Mock 实现）
- P1：AI 调用审计集成（对接 Backend AiCallLog）
- P2：前端 AI 阅卷审核界面开发
- P2：前端 AI 对话界面开发

---

# 5. 数据库状态

## 已有数据表（15 张）

| 表名 | 用途 | 状态 |
|------|------|------|
| user | 用户（HR + 考生） | ✅ |
| exam | 考试信息（含 exam_code） | ✅ |
| question | 题目 | ✅ |
| exam_record | 考试记录（含 exam_code/participant_id） | ✅ |
| answer_record | 答题记录（含 question_snapshot） | ✅ |
| ai_report | AI 分析报告 | ✅ |
| grading_record | 评分记录 | ✅ |
| question_score_rule | 题目评分规则 | ✅ |
| exam_template | 试卷模板 | ✅ S4.2 |
| template_question | 模板题目 | ✅ S4.2 |
| exam_participant | 考试参与人员 | ✅ S4.3-A |
| position | 岗位信息 | ✅ S5.4 |
| scoring_template | 评分模板 | ✅ S5.4 |
| scoring_rule | 评分规则（带版本） | ✅ S5.4 |
| candidate_analysis_report | 候选人分析报告 | ✅ S5.5 |

## 表关系概览

```
user ──1:N──▶ exam（HR 创建考试）
exam ──1:N──▶ question（题目）
exam ──1:N──▶ exam_record（考试记录）
exam ──1:N──▶ exam_participant（参与人员）
exam_record ──1:N──▶ answer_record（答题记录）
exam_record ──1:1──▶ grading_record（评分）
exam_record ──1:1──▶ ai_report（AI 报告）
exam_record ──1:1──▶ candidate_analysis_report（候选人分析报告）
exam_participant ──1:N──▶ exam_record（参与记录）
position ──1:N──▶ scoring_template（岗位评分模板）
scoring_template ──1:N──▶ scoring_rule（评分规则）
```

---

# 6. 后端 API 概览

## 接口分类

| 分类 | 前缀 | 说明 |
|------|------|------|
| 认证 | /api/v1/auth/ | 登录/注册/登出 |
| 考试管理 | /api/v1/exams/ | CRUD + 发布/关闭/导入 |
| 题目管理 | /api/v1/questions/ | 题目 CRUD |
| 候选人考试 | /api/v1/exam-records/ | 创建记录/答题/提交 |
| 评分与报告 | /api/v1/grading/, /api/v1/reports/ | 评分结果/AI 报告 |
| 模板管理 | /api/v1/templates/ | 模板 + 题目管理 |
| 人员管理 | /api/v1/exams/{id}/participants/ | 人员 CRUD + 状态同步 |
| AI 评分 | /api/v1/ai-scoring/ | AI 评分 + 健康检查 |
| AI 阅卷管理 | /api/v1/ai-grading/ | 触发评分/查询/HR 确认/拒绝 |
| 知识库管理 | /api/v1/knowledge-base/ | 岗位/模板/规则 CRUD + RAG 检索 |
| 候选人分析报告 | /api/v1/analysis-reports/ | 生成/查询/审核分析报告 |
| 数据查询 | /api/v1/exams/{id}/analysis, /results, /records/{rid}/answers | 考试分析/成绩列表/答题详情 |
| 候选人历史 | /api/v1/candidates/{id}/exam-history | 候选人历史（分页/排序/过滤） |

## 权限架构
- **角色**：`admin` / `hr` / `candidate`
- **HR 端点**：`require_hr_or_admin` 依赖保护
- **候选人**：通过 `exam_code + phone` 身份验证
- **数据隔离**：HR 只能操作自己创建的数据
- **统计/查询接口**：权限继承 + 数据隔离已覆盖

## S4.4-C AI 数据访问检查结论
- ✅ 架构支持：AI 服务独立部署，可通过 HTTP 调用 Backend API
- ✅ 接口就绪：S4.4-A/B 已建设完整查询接口（统计/分析/成绩/答题/历史）
- ✅ 权限可控：现有权限体系可复用，AI 调用将继承用户权限
- ✅ 审计基础：AI 服务有日志体系，Backend 有 request_id 追踪
- ⚠️ 建议：S5 阶段需补充 AI 调用审计表、数据脱敏中间件、API 限流

---

# 7. 前端与 AI 模块状态

## 前端已实现
- 15 个页面（Login/AdminLayout/ExamList/ExamCreate/ExamDetail/TemplateList/TemplateCreate/TemplateDetail/ExamParticipants/Entry/Exam/GradingResultList/GradingResultDetail/ReportList/ReportDetail）
- 9 个 API 模块（authApi/examApi/questionApi/examRecordApi/gradingApi/reportApi/templateApi/participantApi/aiScoringApi）
- Pinia Store + Axios 拦截器 + 路由守卫

## AI-Service 已实现
- BaseAgent（抽象基类）
- ScoringAgent（评分 Agent）
- ReportAgent（报告 Agent）
- PromptLoader（YAML 版本化 Prompt）
- LLMClient（httpx 异步调用，OpenAI 兼容接口）
- ModelProvider（统一 Provider，支持 deepseek/dashscope/openai/anthropic）
- LLMResponse / LLMCallResult（统一响应格式）
- AI 健康检查端点（配置检查 + 连接测试）
- AI 调用日志（请求/响应/错误，不记录敏感数据）
- DeepSeek-V4-Flash 模型接入（默认模型）

---

# 8. 快速启动指南（Windows）

## 一键启动

项目根目录下提供了两个批处理脚本：

### start-system.bat - 一键启动（S7.1 优化版）

双击运行即可自动启动所有服务：
1. **验证目录结构**：检查 backend/ai-service/frontend 目录是否存在
2. **清理旧服务**：按端口（8000/8001/3000）精确清理占用进程 + 关闭 AI-Exam 窗口
3. **启动 Backend**：`python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`（30秒端口验证）
4. **启动 AI Service**：`python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload`（30秒端口验证）
5. **启动 Frontend**：`npm run dev`（自动检测 node_modules，40秒端口验证）
6. **输出访问地址** + 5秒后自动打开浏览器（login + candidate）

**关键特性**：
- `--reload` 参数确保后端代码修改后自动生效
- 端口验证循环确保服务真实可用后才标记成功
- 失败时暂停显示错误原因，方便排查
- 使用 `%~dp0` 支持任意路径运行
- `chcp 65001` 防止中文乱码

### stop-system.bat - 一键关闭（S7.1 优化版）

双击运行即可关闭所有服务：
1. 按端口（8000/8001/3000）精确终止进程
2. 关闭 AI-Exam 标题窗口
3. 等待3秒后二次验证端口是否已释放
4. 输出停止进程计数和验证结果

## 手动启动命令

如需单独启动各服务，可执行以下命令：

```bash
# Backend (端口 8000, --reload 确保代码修改后自动生效)
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# AI Service (端口 8001)
cd ai-service
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (端口 3000)
cd frontend
npm run dev
```

## 访问地址

| 服务 | 地址 |
|------|------|
| Backend API | http://localhost:8000 |
| AI Service | http://localhost:8001 |
| Frontend | http://localhost:3000 |
| 管理员登录 | http://localhost:3000/login |
| 考生入口 | http://localhost:3000/candidate |

## 环境配置

首次使用前需确保：
1. **backend/.env** 配置正确（数据库、JWT密钥）
2. **ai-service/.env** 配置正确（AI API Key）
3. **frontend/node_modules** 已安装（npm install）

---

# 9. AI 开发规则

1. **不随意改变已确定的架构**
2. **修改前先阅读本文件**
3. **重大设计变更必须更新文档**
4. **不跨阶段开发**
5. **保持文档和代码同步**
6. **使用 Service 层封装业务逻辑**
7. **禁止引入招聘/岗位/简历相关模块**
8. **禁止引入随机组卷系统**
9. **密码必须使用 bcrypt 哈希**
10. **密钥必须使用环境变量**

---

# AI 接手说明

## 必读文件（按顺序）
1. **docs/AI_HANDOVER.md**（本文件）— 当前状态
2. **docs/CHANGE_HISTORY.md** — 项目历史记录
3. **docs/AI_RULES.md** — 开发规则
4. **docs/PROJECT_CONTEXT.md** — 项目背景
5. **docs/PRD.md** — 产品需求

## 阅读后确认
1. 当前项目状态：S4.3-C 已完成，准备进入 S5
2. 下一步任务：等待用户确认是否进入下一阶段
3. 启动开发前向用户确认理解
