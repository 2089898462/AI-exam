# 系统架构设计

## 整体架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│    Backend      │────▶│    MySQL 8      │
│  Vue3 + Vite    │     │  FastAPI        │     │                 │
│  Element Plus   │◀────│  SQLAlchemy     │◀────│                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │ HTTP
                                 ▼
                        ┌─────────────────┐
                        │   AI Service    │
                        │  FastAPI        │
                        │  OpenAI SDK     │
                        └─────────────────┘
```

## 服务划分

| 服务 | 端口 | 职责 |
|------|------|------|
| Frontend | 80/3000 | 用户界面，HR管理后台 + 考生考试页 |
| Backend | 8000 | 业务API，考试CRUD、评分逻辑、数据持久化 |
| AI Service | 8001 | AI评分、AI报告生成 |
| MySQL | 3306 | 数据存储 |

## 通信方式
- Frontend ↔ Backend: REST API (JSON)
- Backend ↔ AI Service: HTTP (内部调用)

## 模块划分
### Backend
- api/v1/endpoints: 路由层
- services: 业务逻辑层
- models: 数据模型层
- schemas: 数据校验层
- db: 数据库连接管理
- core: 核心配置
- exceptions: 统一异常处理

### AI Service
- agents: AI Agent定义
- llm: 大模型调用
- prompts: Prompt模板管理
- services: 业务编排