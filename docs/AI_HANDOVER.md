# AI 上下文交接文档

> **本文件为 AI Agent 必读文档。每次接手本项目必须首先阅读此文件。**
>
> 最后更新：2026-08-04

---

# 1. 项目基本信息

## 项目名称
企业AI智能考试与能力评估系统

## 项目目标
开发一个网页系统，实现：
- HR 后台管理考试（创建、发布、导入）
- 候选人/员工手机端参加考试
- 系统自动评分（客观题）
- AI 生成能力分析报告（主观题评分 + 能力画像）

## 业务场景
1. 招聘面试阶段纸面考试替代
2. 员工试用期培训考试
3. 员工学习成果评估

## 使用人员
- **HR 管理员**：后台创建考试、导入题目、查看成绩
- **候选人/员工**：手机端参加考试、查看结果和 AI 报告

## 核心价值
- 替代人工批改，效率提升 80%+
- AI 主观题评分，标准统一
- 个性化 AI 能力分析报告，帮助员工成长

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

## Frontend

- **技术栈**：Vue 3 + Vite + Element Plus
- **端口**：开发 3000，生产 80
- **目录结构**：
  ```
  frontend/src/
  ├── api/index.js              # API 接口封装
  ├── hooks/index.js            # 组合式函数
  ├── layouts/
  │   ├── AdminLayout.vue       # HR 后台布局
  │   └── ExamLayout.vue        # 考生考试页布局
  ├── router/index.js           # 路由配置
  ├── utils/request.js          # Axios 封装
  ├── App.vue
  └── main.js
  ```
- **状态**：骨架已搭建，未开发业务页面

## Backend

- **技术栈**：Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic
- **端口**：8000
- **目录结构**：
  ```
  backend/app/
  ├── api/
  │   ├── __init__.py           # API 聚合入口（支持多版本）
  │   └── v1/
  │       ├── router.py         # v1 路由注册中心
  │       └── endpoints/
  │           └── health.py     # 健康检查端点
  ├── core/
  │   └── config.py             # 全局配置（pydantic_settings）
  ├── db/
  │   ├── base.py               # SQLAlchemy Base 声明
  │   ├── session.py            # 数据库会话管理
  │   └── init_db.py            # 数据库初始化
  ├── models/                   # ORM 模型（6 张核心表）
  │   ├── user.py
  │   ├── exam.py
  │   ├── question.py
  │   ├── exam_record.py
  │   ├── answer_record.py
  │   └── ai_report.py
  ├── schemas/                  # Pydantic 校验模型
  │   ├── common.py             # 基础类、分页
  │   ├── user.py
  │   ├── exam.py
  │   ├── question.py
  │   └── record.py
  ├── services/                 # 业务服务层
  │   ├── base.py               # 通用 CRUD 基类
  │   ├── user_service.py
  │   ├── exam_service.py
  │   ├── question_service.py
  │   └── record_service.py
  ├── exceptions/               # 统一异常处理
  │   ├── __init__.py           # 5 种业务异常定义
  │   └── handler.py            # 全局异常处理器
  └── utils/
      ├── response.py           # 统一响应格式
      └── password.py           # bcrypt 密码哈希
  ```

## AI-Service

- **技术栈**：Python 3.13 + FastAPI + httpx（AI 服务）
- **端口**：8001
- **目录结构**：
  ```
  ai-service/
  ├── main.py                   # 入口
  └── app/
      ├── api/
      │   └── router.py         # API 路由
      ├── agents/
      │   ├── base_agent.py     # Agent 抽象基类
      │   ├── scoring_agent.py  # 评分 Agent（骨架）
      │   └── report_agent.py   # 报告 Agent（骨架）
      ├── core/
      ├── evaluation/           # 评估用例
      ├── llm/
      │   ├── client.py         # LLMClient 封装
      │   └── models.py         # ModelConfig
      ├── prompts/              # YAML 版本化 Prompt
      │   ├── scoring/v1.yaml
      │   └── report/v1.yaml
      └── services/
  ```

## Database

- **类型**：MySQL 8.0
- **存储引擎**：InnoDB
- **字符集**：utf8mb4
- **部署方式**：Docker 容器化（docker-compose）
- **ORM**：SQLAlchemy 2.0
- **迁移工具**：Alembic
- **连接配置**：`mysql+pymysql://root:password@localhost:3306/exam_system`

---

# 3. 已确认的重要技术决策

以下决策已经确定，**未来不要随意修改**。如需修改必须更新本文件。

## 决策列表

| # | 决策内容 | 原因 | 影响 |
|---|----------|------|------|
| 1 | MVP 采用固定试卷模式 | 自动组卷复杂度高，首期聚焦核心流程 | S2 考试管理需实现手动组卷 |
| 2 | 第一版不开发自动组卷 | 降低 MVP 范围，快速验证核心业务 | 未来 S4 阶段开发 |
| 3 | 第一版不开发 RAG 知识库 | RAG 架构复杂度高，首期用 Prompt 工程 | 未来根据业务需要引入 |
| 4 | Word 解析不进入 MVP | 题目 JSON 导入更简洁可靠 | HR 通过 JSON 导入考试 |
| 5 | AI 服务独立部署 | 解耦业务逻辑与 AI 能力，独立扩缩容 | Backend 通过 HTTP 调用 AI-Service |
| 6 | Prompt 与代码分离 | YAML 版本化管理，便于迭代和回退 | prompts/ 目录按版本组织 |
| 7 | 使用 Alembic 管理数据库 | 版本化迁移，支持回滚 | 统一使用 `alembic upgrade head` |
| 8 | 数据库 JSON 字段使用通用 sa.JSON() | 跨数据库兼容，不绑定 MySQL 特有类型 | 模型文件 import sqlalchemy.JSON |
| 9 | 密码使用 bcrypt 哈希 | 安全行业标准，防止明文存储 | 禁止在代码中存明文密码 |
| 10 | API 统一前缀 /api/v1 | 支持未来版本扩展 | 所有业务接口挂此路径下 |
| 11 | 统一响应格式 ApiResponse | 前后端分离，统一错误处理 | 所有接口使用 success/error 包装 |
| 12 | Service 层封装业务逻辑 | API 层不直接操作数据库 | 新增业务必须创建 Service |
| 13 | AI 评分与报告 Agent 分离 | 职责单一，便于独立迭代 | scoring_agent + report_agent |
| 14 | SQL 文件仅作参考，不作为初始化入口 | 统一迁移方案 | sql/init.sql 已标记废弃 |

---

# 4. 当前开发阶段

## 当前阶段
**S3.2.2 候选人答题页面基础开发 完成**

## 已完成
- [x] 项目目录结构搭建
- [x] 前端骨架（Vue3 + Vite + Element Plus）
- [x] 后端骨架（FastAPI + SQLAlchemy）
- [x] AI 服务骨架
- [x] 数据库设计（ER 关系 + 6 张核心表）
- [x] SQLAlchemy ORM 模型（Model 层）
- [x] Alembic 迁移（6 个版本，S1→S2→S3.1.1 全链路）
- [x] API 路由架构（router.py + /api/v1）
- [x] Schema 规范（Pydantic 请求/响应校验）
- [x] Service 层规范（业务逻辑封装）
- [x] 异常处理（统一异常 + 全局处理器 + data参数支持）
- [x] 统一响应格式（ApiResponse）
- [x] 健康检查（基础 + 数据库连接检查）
- [x] 密码安全（bcrypt 哈希 + 禁止明文）
- [x] JSON 类型通用化（sa.JSON）
- [x] AI-Service 基础结构（LLMClient、BaseAgent）
- [x] 考试 CRUD 接口（创建/查询/更新/删除/发布/关闭）
- [x] 题目管理接口（CRUD + 批量操作 + 题型校验）
- [x] JSON 导入接口（文件上传 + 事务回滚 + 三题型支持）
- [x] 认证基础：JWT（HS256）+ bcrypt + 角色（admin/candidate/hr）+ 状态（active/disabled/pending）
- [x] 认证 API：/auth/register /auth/login /auth/me /auth/logout
- [x] API 权限保护：所有 HR 后台端点已加 JWT + 角色校验
- [x] 依赖模块（app/core/dependencies.py）+ 权限模块（app/core/permissions.py）
- [x] JWT 配置集中化（settings 环境变量，无硬编码）
- [x] Service 层数据隔离（admin 绕过所有权，HR 仅操作自己）
- [x] 浏览器端到端测试（S2.3 全流程 + 认证接口 + 权限保护自动化测试）
- [x] 前端登录页（Login.vue：表单校验 + 用户名密码登录）
- [x] Pinia 用户 Store（useUserStore：login/logout/getUserInfo + getter）
- [x] Token 管理（auth.js：localStorage 持久化）
- [x] Axios 拦截器（请求附加 Authorization + 401 自动跳转）
- [x] 路由守卫（无 token 跳转登录 + 已有 token 访问登录跳转首页）
- [x] AdminLayout 集成（用户下拉 + 退出登录确认）
- [x] 登录流程端到端测试（无 token→跳转 + 登录成功 + 刷新保持 + 401 退出）
- [x] 数据库修复：exam_record/ai_report 表新增 updated_at 字段
- [x] 文件上传安全修复：JSON 导入接口增加 5MB 大小限制
- [x] **S3.1.1 候选人考试流程数据库扩展**：
  - exam_record 表重构：移除 user_id、新增候选人嵌入式身份字段、扩展状态枚举
  - answer_record 表重构：answer→answer_content、移除 score_type、score_detail→ai_comment、新增 is_correct
  - user 模型：移除 exam_records 关系
  - Schemas 层：新增候选人字段 Schema、ExamRecordListResponse
  - Alembic 迁移：e1f2a3b4c5d6 完整表重建策略
  - 数据关系：exam(1:N)→exam_record(1:N)→answer_record(1:N)←question
- [x] **S3.1.2 Service 层开发**：
  - ExamRecordService：create_exam_record / get_record_by_id / start_exam / submit_exam / list_exam_records / get_detail_with_answers
  - AnswerRecordService：save_answer / save_answers_batch / get_answers_by_record
  - RecordService 重构为兼容层，委托调用新 Service
  - 业务校验：考试存在性、题目归属、状态机流转、答题权限
  - 事务一致性：批量操作 rollback 保护
  - 单元测试：28 个测试用例全通过（SQLite 内存数据库）
- [x] **S3.1.3 API 接口开发**：
  - Schema：ExamRecordCreate / ExamRecordResponse / ExamRecordDetailResponse / ExamRecordListResponse / AnswerCreate / AnswerBatchCreate / AnswerResponse（全部继承 BaseSchema）
  - 候选人端点（无需认证）：POST /exam-records / GET /exam-records/{id} / POST /exam-records/{id}/start / POST /exam-records/{id}/answers / POST /exam-records/{id}/answers/batch / POST /exam-records/{id}/submit
  - HR 管理端点（需 JWT + HR/Admin）：GET /exams/{exam_id}/records
  - 路由注册：exam_record_router（候选人）+ exam_record_hr_router（HR）
  - 异常处理：NotFoundException(404) / BusinessException(400) / ValidationException(422) / ForbiddenException(403) / UnauthorizedException(401)
  - 权限控制：候选人无需登录（嵌入式身份）、HR 端点 require_hr_or_admin 依赖
  - API 测试：20 个测试用例全通过 + Service 层 28 个测试全通过（无回归）
- [x] **S3.2.1 候选人考试入口页面**：
  - 前端页面：Entry.vue（考试信息展示 + 候选人身份表单 + 成功面板）
  - API 封装：examRecord.js（getExamInfo / createRecord / getRecord / startExam / submitExam / saveAnswer / saveAnswersBatch / listRecords）
  - Pinia Store：exam.js（examId / recordId / 候选人信息 / 考试状态 + 操作方法）
  - 公开后端端点：GET /api/v1/exams/{exam_id}/info（无需认证）
  - 路由注册：/exam/:id → ExamEntry（候选人入口，无需登录）
  - 浏览器测试：全流程验证通过（表单 → API → 成功面板）
- [x] **S3.2.2 候选人答题页面基础开发**：
  - 后端公开端点：GET /api/v1/exam-records/{id}/paper（无需认证，返回考试试卷）
  - Schema：PaperQuestionResponse / ExamPaperResponse（安全过滤，不含正确答案）
  - 前端 API 扩展：examRecordApi.getExamPaper(recordId)
  - Pinia Store 扩展：examInfo / questions / answers 状态 + loadExamPaper / setAnswer actions
  - 答题组件：QuestionCard.vue（动态渲染）+ ChoiceQuestion.vue（单选/多选）+ TextQuestion.vue（简答）
  - 答题页面：Exam.vue（答题卡导航 + 题目卡片 + 上一题/下一题 + 完成确认）
  - 路由注册：/exam/record/:id → ExamTaking（答题页，无需登录）
  - 入口页跳转路径修复：/exam/${examId}/exam → /exam/record/${recordId}
  - 浏览器测试：三种题型渲染正常 + 答案切换不丢失 + 答题卡导航正常

## 进行中
无

## 下一阶段
**S3.2.3 答案保存与提交流程** — 答案自动保存、提交考试

S3.2.3 规划开发内容：
- 答案自动保存（切换题目时自动保存当前答案到后端）
- 答案批量保存接口对接（saveAnswersBatch）
- 提交考试流程（submitExam + 状态流转）
- 考试完成页面（提交成功提示 + 成绩预览）
- 前端 API 对接（examRecordApi.saveAnswersBatch / submitExam）
- HR 后台考试记录查看页面

## 权限架构说明
- **角色枚举**：`admin` / `hr` / `candidate`
- **HR 后台保护**：`require_hr_or_admin` 依赖保护所有 exam + question 端点
- **认证接口**：`/auth/login`、`/auth/register` 可匿名访问；`/auth/me` 需要 Token
- **数据隔离**：
  - admin：可查看/操作所有考试
  - hr：只能查看/操作自己创建的考试
  - candidate：无法访问任何 HR 后台接口（403）
- **依赖模块** `app/core/dependencies.py`：
  - `get_current_user`：强制鉴权（返回 User 实体）
  - `get_current_user_id_from_header`：轻量鉴权（仅返回 ID）
  - `get_optional_current_user`：可选鉴权（无 Token 返回 None）
- **权限模块** `app/core/permissions.py`：
  - `require_admin`：仅 admin
  - `require_hr_or_admin`：HR 或 admin
  - `require_roles([roles])`：角色校验工厂
  - `require_authenticated`：仅需登录
- **配置来源**：JWT_SECRET_KEY、JWT_ALGORITHM、JWT_ACCESS_TOKEN_EXPIRE_MINUTES 均来自 `Settings`（`.env` 环境变量）

## 前端状态
- **技术栈**：Vue3 + Vite + Element Plus + Vue Router + Axios + Pinia
- **端口**：3000
- **代理**：/api → http://localhost:8000
- **已实现页面**：
  - Login（登录页：用户名/密码登录 + 表单校验 + 登录跳转）
  - AdminLayout（Header + Sidebar + 菜单 + RouterView + 用户下拉 + 退出登录）
  - ExamList（考试列表：搜索/筛选/分页/岗位列/状态标签/操作按钮：查看/编辑/发布/关闭/删除）
  - ExamCreate（创建/编辑考试：表单 + 岗位字段 + 题目列表占位 + JSON 导入入口）
  - ExamDetail（考试详情：只读信息 + 岗位字段 + 题目列表 + 导入试卷按钮 + 关闭操作）
  - Entry（候选人考试入口页：考试信息展示 + 身份表单 + 创建记录 + 成功面板）
  - Exam（候选人答题页：答题卡导航 + 题目卡片 + 三种题型 + 上一题/下一题 + 完成确认）
- **已实现组件**：
  - ImportExamDialog（JSON 导入对话框：拖拽上传、结果展示、错误详情）
  - QuestionTable（题目列表：8 列 + 删除操作 + 只读模式）
  - QuestionCard（题目卡片：根据题型动态渲染选择题/简答题组件）
  - ChoiceQuestion（选择题：单选/多选/判断题，选项兼容解析）
  - TextQuestion（简答题：多行文本输入）
- **已实现 API**：
  - authApi：login / getCurrentUser
  - examApi：getExamList / getExamDetail / createExam / updateExam / deleteExam / publishExam / closeExam / importExam
  - questionApi：getQuestions / createQuestion / deleteQuestion
  - examRecordApi：getExamInfo / createRecord / getRecord / getExamPaper / startExam / submitExam / saveAnswer / saveAnswersBatch / listRecords
- **已实现基础设施**：
  - Token 管理（utils/auth.js：localStorage）
  - Pinia 用户 Store（stores/user.js：login/logout/getUserInfo）
  - Pinia 考试 Store（stores/exam.js：examId / recordId / 候选人信息 / examInfo / questions / answers + createRecord / loadExamPaper / setAnswer / startExam / submitExam）
  - Axios 拦截器（自动附加 Authorization + 401 处理）
  - 路由守卫（router/guard.js：认证检查 + 重定向）
- **未实现功能**：
  - 题目手动新增/编辑组件
  - 答案自动保存与提交（S3.2.3）
  - 成绩/报告查看页面

## 未开发模块
- AI 评分逻辑
- AI 报告生成逻辑
- 答案保存与提交流程（S3.2.3）
- 考生端考试入口（S3.2.1 已完成）
- 考生答题页面基础（S3.2.2 已完成）
- Docker 生产部署
- 自动化测试

---

# 5. 数据库状态

## 已有数据表（6 张）

| 表名 | 用途 | 状态 |
|------|------|------|
| user | 用户（HR + 考生） | ✅ 已创建 |
| exam | 考试信息 | ✅ 已创建 |
| question | 题目 | ✅ 已创建 |
| exam_record | 考试记录（一次考试=一个记录） | ✅ 已创建 |
| answer_record | 答题记录（每题一条） | ✅ 已创建 |
| ai_report | AI 分析报告 | ✅ 已创建 |

## 核心字段说明

### user 表
- `id`: 主键
- `username`: 登录名（唯一）
- `password_hash`: bcrypt 哈希值
- `display_name`: 显示名
- `role`: admin / candidate
- `is_active`: 是否启用

### exam 表
- `status`: draft / published / closed
- `duration_minutes`: 考试时长
- `pass_score`: 及格分数
- `created_by`: 外键 → user.id

### question 表
- `type`: single_choice / multiple_choice / true_false / short_answer
- `options`: JSON 数组（选择题选项）
- `answer`: 标准答案（文本）
- `score`: 分值

### exam_record 表
- `status`: in_progress / submitted / graded
- `total_score`: 最终总分

### answer_record 表
- `answer`: 用户答案
- `score`: 得分
- `score_type`: auto / ai
- `score_detail`: JSON 评分详情

### ai_report 表
- `strengths`: JSON 数组（优势）
- `weaknesses`: JSON 数组（薄弱）
- `learning_suggestions`: JSON 数组（学习建议）

## 表之间关系

```
user ──1:N──▶ exam（一个 HR 创建多场考试）
exam ──1:N──▶ question（一场考试多道题）
user ──1:N──▶ exam_record（一个考生多次考试）
exam ──1:N──▶ exam_record（一场考试多人参加）
exam_record ──1:N──▶ answer_record（一次考试多题答案）
question ──1:N──▶ answer_record（一道题多份答案）
exam_record ──1:1──▶ ai_report（一次考试一份报告）
```

## 迁移状态
- **Alembic 版本**：db2a7edfcf67
- **迁移文件**：`backend/alembic/versions/db2a7edfcf67_init_mvp_tables.py`
- **执行命令**：`cd backend && python -m alembic upgrade head`

---

# 6. 后端状态

## 已完成

### API 结构
- 路由注册中心：`api/v1/router.py`
- 统一前缀：`/api/v1`
- 已注册路由：
  - health 路由：`GET /api/v1/health`
  - auth 路由：`POST /api/v1/auth/login`、`POST /api/v1/auth/register`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout`
  - exam 路由：`POST/GET/PUT/DELETE /api/v1/exams`，`POST /api/v1/exams/{id}/publish`，`POST /api/v1/exams/{id}/close`，`POST /api/v1/exams/{id}/import`，`GET /api/v1/exams/{id}/questions`，`GET /api/v1/exams/{id}/info`（公开）
  - question 路由：`POST /api/v1/questions`，`DELETE /api/v1/questions/{id}`
  - exam_record 路由（候选人，无需认证）：`POST /api/v1/exam-records`、`GET /api/v1/exam-records/{id}`、`GET /api/v1/exam-records/{id}/paper`、`POST /api/v1/exam-records/{id}/start`、`POST /api/v1/exam-records/{id}/answers`、`POST /api/v1/exam-records/{id}/answers/batch`、`POST /api/v1/exam-records/{id}/submit`
  - exam_record HR 路由（需 JWT + HR/Admin）：`GET /api/v1/exams/{exam_id}/records`

### Service 层
- `BaseService`：通用 CRUD（get / get_multi / create / update / delete / count / bulk_insert_mappings）
- `UserService`：get_by_username / get_by_email / create_user / authenticate
- `ExamService`：create_exam / update_exam / delete_exam / publish_exam / close_exam / get_exam_detail / list_exams / count_questions
- `QuestionService`：get_by_exam / create_question / update_question / delete_question / batch_create / delete_by_exam
- `ExamImportService`：import_exam（JSON 解析 + 数据校验 + 事务批量入库）
- `ExamRecordService`：create_exam_record / get_record_by_id / start_exam / submit_exam / list_exam_records / get_detail_with_answers
- `AnswerRecordService`：save_answer / save_answers_batch / get_answers_by_record
- `RecordService`：兼容层，委托 ExamRecordService + AnswerRecordService
- `AuthService`：register / login / get_current_user

### Model 层
- 6 个 ORM 模型，外键关系正确
- 所有 JSON 字段使用通用 `sa.JSON()`
- 所有时间字段 `created_at` / `updated_at`

### 数据库连接
- SQLAlchemy 引擎配置
- 会话工厂 `SessionLocal`
- FastAPI 依赖注入 `get_db`

### 安全
- bcrypt 密码哈希
- CORS 中间件（允许 localhost:3000, localhost:80）

## 未完成
- 候选人考试前端页面
- AI 评分接口调用
- 结果查询接口（候选人查看成绩）
- AI 服务调用接口
- AI 报告生成逻辑
- 前端业务页面（候选人端）

---

# 7. AI 模块状态

## 当前

### AI-Service 结构
- 独立 FastAPI 服务
- 端口 8001
- API 路由已创建

### Agents
- `BaseAgent`：抽象基类（run / validate_input）
- `ScoringAgent`：骨架，未实现评分逻辑
- `ReportAgent`：骨架，未实现报告生成逻辑

### Prompt 管理
- YAML 文件按版本管理
- `prompts/scoring/v1.yaml`
- `prompts/report/v1.yaml`

### Evaluation
- `evaluation/scoring_cases.json`：评分测试用例
- `evaluation/report_cases.json`：报告测试用例

### LLM 客户端
- `LLMClient`：httpx 异步调用封装
- 支持任意 OpenAI 兼容接口
- 60 秒超时
- ModelConfig 配置模型参数

## 当前未实现
- 评分 Agent 核心逻辑（评分 prompt 组装 + 调用 + 结果解析）
- 报告 Agent 核心逻辑（报告 prompt 组装 + 调用 + 结果解析）
- 评分/报告异步任务队列
- AI 服务与 Backend 的调用链路

---

# 8. 前端状态

## Vue 项目结构
```
frontend/src/
├── api/index.js              # API 调用封装（空）
├── hooks/index.js            # 组合式函数（空）
├── layouts/
│   ├── AdminLayout.vue       # HR 后台布局（骨架）
│   └── ExamLayout.vue        # 考生考试布局（骨架）
├── router/index.js           # 路由配置（空）
├── utils/request.js          # Axios 封装（空）
├── App.vue
└── main.js
```

## 已完成
- Vue 3 + Vite 初始化
- Element Plus 集成
- 路由骨架
- 布局组件骨架（AdminLayout、ExamLayout）
- @ 路径别名配置

## 未完成
- HR 后台所有页面（登录、考试管理、题目管理、成绩查看）
- 考生端所有页面（考试列表、考试进行中、结果查看）
- API 接口对接
- 状态管理
- 样式完善

## 页面规划
### HR 后台
1. 登录页
2. 考试列表页
3. 创建/编辑考试页
4. 题目管理页
5. 成绩查看页

### 考生端
1. 考试列表页
2. 考试进行中页
3. 成绩详情页
4. AI 报告查看页

---

# 9. 当前已知问题

| # | 问题 | 影响 | 计划处理阶段 |
|---|------|------|-------------|
| 1 | 密码认证未实现 | 用户无法登录 | S2 用户认证 |
| 2 | JWT Token 未实现 | 无状态认证缺失 | S2 用户认证 |
| 3 | 接口无权限控制 | 任何人可访问 API | S2 用户认证 |
| 4 | MySQL 未本地启动 | 数据库连接检查显示 disconnected | 部署阶段 |
| 5 | AI 评分逻辑未实现 | 主观题无法 AI 评分 | S3 AI 业务 |
| 6 | 无 Docker 开发环境 | 本地开发需手动启动 MySQL | DevOps 阶段 |
| 7 | 无自动化测试 | 无法快速回归验证 | 各阶段同步 |
| 8 | 前端无业务页面 | 无法进行端到端测试 | S2 前端开发 |

---

# 10. 后续开发路线

## S2：考试资源管理模块
**开发内容：**
- 用户登录/认证（JWT）
- 考试 CRUD 接口
- 题目管理接口
- 考试 JSON 导入接口
- 考试发布/关闭状态流转
- 前端：HR 后台页面
- 前端：考生端基础页面

## S3：考试参与与评分模块
**开发内容：**
- 考生进入考试流程
- 答题接口（逐题保存）
- 提交考试接口
- 客观题自动评分
- 主观题 AI 评分（调用 AI-Service）
- 考试结果查询接口
- AI 报告生成
- 前端：考试进行中页面
- 前端：成绩/报告查看页面

## S4：优化与部署
**开发内容：**
- Docker 生产部署
- CI/CD 流水线
- 性能优化
- 安全加固（限流、CORS 细化）
- 日志监控
- 自动化测试补充
- 数据初始化脚本

---

# 11. AI 开发规则

## 未来 AI 修改代码必须遵守

1. **不随意改变已经确定的架构**
   - 不修改目录结构（除非有充分理由）
   - 不修改技术栈选择
   - 不跨服务边界

2. **修改前先阅读 AI_HANDOVER.md**
   - 每次接手项目必须完整阅读
   - 理解当前状态、已做决策、未完成事项

3. **修改重大设计必须更新本文件**
   - 架构变更 → 更新第 2 节
   - 技术决策变更 → 更新第 3 节
   - 阶段推进 → 更新第 4 节
   - 数据库变更 → 更新第 5 节
   - 新增/删除模块 → 更新对应章节

4. **不跨阶段开发**
   - 当前阶段未完成时，不提前开发下一阶段功能
   - 遵循 S2 → S3 → S4 的顺序

5. **保持文档和代码同步**
   - 每完成一个功能更新 change-log.md
   - 每完成一个阶段更新 AI_HANDOVER.md
   - 数据库变更必须同步更新 database.md

6. **代码规范**
   - 使用 Service 层封装业务逻辑
   - 使用 Schema 层进行数据校验
   - 使用统一响应格式 ApiResponse
   - 使用统一异常处理
   - 密码必须使用 bcrypt 哈希

---

# AI 接手说明

如果新的 AI Agent 接手本项目，**必须首先阅读以下文件**（按顺序）：

### 必读文件
1. **docs/AI_HANDOVER.md**（本文件）— 项目整体上下文
2. **docs/project-context.md** — 项目背景与目标
3. **docs/architecture.md** — 技术架构设计
4. **docs/PRD.md** — 产品需求（MVP 范围）

### 按需阅读
5. **docs/database.md** — 数据库设计
6. **docs/api.md** — API 接口设计
7. **docs/ai-design.md** — AI Agent 设计
8. **docs/change-log.md** — 变更历史

### 阅读后必须确认

1. **当前项目状态**
   - 阶段：S1 完成
   - 已完成：基础架构全部搭建
   - 准备进入：S2 考试资源管理

2. **下一步任务**
   - 等待用户确认进入 S2
   - S2 开发内容：用户认证、考试管理、题目管理

3. **禁止修改事项**
   - 不修改已确定的技术决策（见第 3 节）
   - 不跨阶段开发
   - 不删除已有文档
   - 不修改数据库模型结构（除非用户明确要求）
   - 不引入未确认的新依赖

4. **启动开发前确认**
   - 阅读完毕后向用户确认当前理解
   - 等待用户下达 S2 开发指令
