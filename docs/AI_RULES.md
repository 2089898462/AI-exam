# AI 项目开发规则

> **本文件为 AI Agent 开发时必须遵守的长期规则。**
> 
> 创建日期：2026-08-05

---

# 1. 项目定位

## 项目名称
企业AI智能考试与能力评估系统

## 项目目标
开发一个网页系统，实现：
- HR 后台管理考试（创建、发布、导入）
- 候选人/员工手机端参加考试
- 系统自动评分（客观题）
- AI 生成能力分析报告（主观题评分 + 能力画像）

## 当前开发阶段
> 详细阶段信息请参考 `docs/AI_HANDOVER.md`

**S3.2.2 候选人答题页面基础开发 已完成**

当前重点：**S3.2.3 答案保存与提交流程**

---

# 2. 技术栈约束

## 固定技术栈

### Frontend
- **框架**：Vue3
- **构建工具**：Vite
- **UI 组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP 客户端**：Axios

### Backend
- **框架**：FastAPI
- **ORM**：SQLAlchemy 2.0
- **数据库迁移**：Alembic
- **数据校验**：Pydantic

### Database
- **类型**：MySQL 8.0
- **引擎**：InnoDB
- **字符集**：utf8mb4

### AI-Service
- **框架**：FastAPI
- **LLM 调用**：OpenAI SDK / httpx

## 禁止引入
- 未经确认的新框架或新库
- 与现有技术栈冲突的替代方案

---

# 3. 架构约束

## Backend 分层架构

```
API (api/v1/endpoints/)
    ↓
Schema (schemas/)
    ↓
Service (services/)
    ↓
Model (models/)
    ↓
Database (db/)
```

### 规定
1. **API 层禁止直接操作数据库**
   - API 层只做：参数校验、调用 Service、返回响应
   - 所有数据库操作必须通过 Service 层

2. **Service 层禁止处理 HTTP 逻辑**
   - Service 层只做：业务逻辑、数据持久化、事务管理
   - 不处理 HTTP 状态码、请求/响应格式

3. **统一响应格式**
   - 所有 API 响应使用 `ApiResponse` 格式
   - 使用 `success()` / `error()` / `created()` 等工具方法

4. **统一异常处理**
   - 使用 `AppException` 体系（NotFoundException / BusinessException / ValidationException / ForbiddenException / UnauthorizedException）
   - 禁止直接抛出 `HTTPException`

## Frontend 分层架构

```
页面 (views/)
    ↓
组件 (components/)
    ↓
Store (stores/)
    ↓
API 封装 (api/)
```

### 规定
1. **页面禁止直接调用 axios**
   - 所有 HTTP 请求必须通过 `api/` 模块封装
   - 页面只调用 `api/` 中导出的方法

2. **组件职责单一**
   - 组件只负责 UI 渲染和用户交互
   - 业务逻辑放在 Store 或 composables 中

3. **状态管理使用 Pinia**
   - 全局状态（用户信息、考试信息）必须放在 Pinia Store
   - 组件内状态使用 `ref` / `reactive`

---

# 4. 数据库规范

## 必备字段
所有业务表必须包含：
- `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
- `updated_at` DATETIME NOT NULL ON UPDATE CURRENT_TIMESTAMP

## 数据库修改规则
1. **必须通过 Alembic migration**
   - 禁止直接修改生产数据库
   - 所有结构变化必须创建 Alembic 迁移文件

2. **迁移文件命名规范**
   - 使用有意义的哈希前缀，如 `e1f2a3b4c5d6_add_xxx.py`
   - 文件名描述修改内容

3. **JSON 字段统一**
   - 使用通用 `sa.JSON()` 类型
   - 禁止使用 MySQL 特有 `JSON` 类型

## 命名规范
- 表名：小写 + 下划线，如 `exam_record`
- 主键：统一 `id BIGINT AUTO_INCREMENT`
- 外键：`{目标表名}_id`，如 `exam_id`
- 索引前缀：`idx_`，唯一索引加 `UNIQUE`

---

# 5. AI 开发流程

每次开发任务必须遵守以下流程：

## Step 1: 确认当前阶段
读取 `docs/AI_HANDOVER.md`，确认：
- 当前开发阶段
- 已完成模块
- 进行中任务
- 下一阶段规划

## Step 2: 了解历史修改
读取 `docs/change-log.md`，了解：
- 近期修改记录
- 修复的 Bug
- 新增的功能

## Step 3: 检查已有代码
在执行任务前，必须：
- 检查相关模块的现有代码
- 确认代码风格和规范
- 避免重复创建已有功能

## Step 4: 执行当前任务
按照用户指令执行开发任务，遵守本规则所有约束。

---

# 6. 文档同步规则

## 自动更新（开发任务完成后）

### docs/change-log.md
记录：
- 日期
- 阶段
- 修改内容
- 测试结果

### docs/AI_HANDOVER.md
更新：
- 当前阶段
- 已完成内容
- 下一阶段
- 前端/后端状态

## 开发 Prompt 无需重复提醒
本规则文件已固定，开发时不需要再次提醒以下内容：
- 技术栈
- 架构规则
- 数据库规范
- 文档同步规则
- 禁止事项

---

# 7. 禁止事项

## 通用禁止
1. **禁止未经确认重构已有模块**
   - 重构必须有充分理由并获得用户确认
   - 不得随意修改已确定的架构

2. **禁止重复创建已有功能**
   - 开发前必须检查现有代码
   - 如果功能已存在，应扩展而非重写

3. **禁止提前开发未规划模块**
   - 严格遵循当前阶段开发
   - 不得跨阶段提前实现未来功能

4. **禁止引入未经确认技术**
   - 新框架、新库、新工具必须获得用户确认
   - 保持技术栈一致性

## MVP 阶段禁止
以下功能在 MVP 阶段禁止开发：
- **RAG（检索增强生成）**
- **自动组卷**
- **复杂 Agent 编排**
- **AI 监考**
- **Word 文档解析**
- **Docker 生产部署（S4 阶段）**

## 安全禁止
- **禁止明文存储密码**（必须使用 bcrypt 哈希）
- **禁止在代码中硬编码密钥**（必须使用环境变量）
- **禁止在日志中记录敏感信息**
- **禁止绕过权限校验**（所有 HR 端点必须鉴权）

---

# 8. 版本历史

| 日期 | 版本 | 修改内容 |
|------|------|----------|
| 2026-08-05 | 1.0 | 创建初始版本 |
