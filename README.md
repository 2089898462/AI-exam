# 企业AI智能考试与能力评估系统

## 项目简介
企业内部AI考试系统，支持HR后台管理考试、员工手机端在线考试、AI自动评分及能力分析报告生成。

## 技术栈
- 前端：Vue3 + Vite + Element Plus
- 后端：Python + FastAPI + SQLAlchemy
- 数据库：MySQL 8
- AI服务：独立Python服务（OpenAI SDK）
- 部署：Docker

## 项目结构

```
├── frontend/          # Vue3 前端
├── backend/           # FastAPI 后端
├── ai-service/        # AI 评分与报告服务
├── docker/            # Docker 编排配置
├── docs/              # 项目文档
├── tests/             # 测试目录
└── sql/               # 数据库脚本
```

## 快速开始

### 开发环境
```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev

# AI服务
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Docker 部署
```bash
# 开发环境
docker compose -f docker/docker-compose.dev.yml up -d

# 生产环境
docker compose -f docker/docker-compose.prod.yml up -d
```

## 开发阶段
- S0: 基础设施搭建 ✅
- S1: 数据层 + 核心 API
- S2: 前端框架 + 考试管理
- S3: 在线考试模块
- S4: AI 评分服务
- S5: AI 报告 + 联调交付

## AI 开发说明

本项目采用 **文档驱动 + AI Agent 协作开发模式**。

### AI 开发入口
AI Agent 接手项目时，必须按顺序阅读以下文件：

1. **[AI_RULES.md](docs/AI_RULES.md)** — AI 开发规则（技术栈、架构约束、禁止事项）
2. **[PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)** — 项目长期上下文（项目定位、核心设计、开发路线）
3. **[AI_HANDOVER.md](docs/AI_HANDOVER.md)** — 当前阶段上下文交接（实时更新）
4. **[change-log.md](docs/change-log.md)** — 变更历史

### 开发流程
1. 阅读上述入口文档，确认当前阶段和规则
2. 执行开发任务
3. 完成后自动更新 `change-log.md` 和 `AI_HANDOVER.md`

### 注意事项
- 本项目规则已固化在 `AI_RULES.md` 中，开发 Prompt 无需重复说明
- 所有代码修改必须遵守架构分层和数据库规范
- 禁止跨阶段开发和引入未确认技术

## 文档
### AI 开发文档
- [AI 开发规则](docs/AI_RULES.md)
- [项目长期上下文](docs/PROJECT_CONTEXT.md)
- [AI 上下文交接](docs/AI_HANDOVER.md)
- [变更记录](docs/change-log.md)

### 设计文档
- [项目背景](docs/project-context.md)
- [产品需求](docs/PRD.md)
- [系统架构](docs/architecture.md)
- [数据库设计](docs/database.md)
- [API 设计](docs/api.md)
- [AI Agent 设计](docs/ai-design.md)