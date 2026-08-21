# AI考试系统（企业内部版）

<p align="center">
  <strong>基于 AI 能力的企业内部考试管理系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0.0-blue" alt="version" />
  <img src="https://img.shields.io/badge/status-stable-green" alt="status" />
  <img src="https://img.shields.io/badge/license-Proprietary-orange" alt="license" />
</p>

---

## 📋 项目介绍

AI考试系统（企业内部版）是一套面向企业人事部门的一站式智能考试管理平台，覆盖从考试创建、员工在线考试、自动评分、AI能力分析报告到HR成绩查看的完整业务流程。

**业务价值**：
- 替代人工批改，效率提升 80%+
- AI 主观题评分，标准统一、结果可追溯
- AI 考试分析报告，辅助 HR 快速了解考试情况
- 员工学习成果可视化，支持培训效果闭环

## ✨ 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **考试管理** | 创建考试 / 模板管理 / 题库管理 / JSON导入 / 发布关闭 | ✅ |
| **在线考试** | 手机&PC浏览器 / 身份验证 / 自动保存 / 倒计时 / 断点恢复 | ✅ |
| **评分系统** | 客观题自动评分 / AI主观题评分 / HR复核 | ✅ |
| **AI能力** | AI评分（v1-v3 Prompt） / AI分析报告 / 考试总结 | ✅ |
| **监考系统** | 切屏检测 / 数据持久化 / 异常分析 / HR详情 | ✅ |
| **诚信弹窗** | 考试前威慑提示 / 不可关闭 / 移动端适配 | ✅ |

## 🏗️ 技术架构

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
                        │  DeepSeek AI    │
                        └─────────────────┘
```

**技术栈**：

| 层 | 技术 | 版本 |
|----|------|------|
| 前端 | Vue3 + Vite + Element Plus + Pinia | 3.x |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic | Python 3.10+ |
| AI | FastAPI + DeepSeek AI | - |
| 数据库 | MySQL 8.0 | InnoDB / utf8mb4 |

## 📁 项目结构

```
AI-Exam-System/
├── frontend/           # Vue3 前端（HR后台 + 考生考试页）
├── backend/            # FastAPI 后端（业务API + 数据持久化）
├── ai-service/         # AI 服务（评分 + 报告生成）
├── docker/             # Docker 部署配置
├── docs/               # 项目文档体系
│   ├── 01_项目概览/
│   ├── 02_技术架构/
│   ├── 03_业务设计/
│   ├── 04_监考系统/
│   ├── 05_开发记录/
│   ├── 06_测试记录/
│   ├── 07_部署维护/
│   └── 08_AI协作规范/
├── tests/              # 测试目录
├── VERSION.md          # 版本说明
├── AI_RULES.md         # AI 开发规则
├── PROJECT_CONTEXT.md  # 项目上下文
└── AI_HANDOVER.md      # AI 交接文档
```

## 🚀 本地运行

### 环境要求
- Windows 10/11
- Python 3.10+
- Node.js 18+
- MySQL 8.0+

### 一键启动（推荐）
```bash
# 双击运行
start-system.bat
```

### 手动启动
```bash
# 1. 启动后端（端口 8000）
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. 启动 AI 服务（端口 8001）
cd ai-service
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 3. 启动前端（端口 5173）
cd frontend
npm install
npm run dev
```

### 访问地址
| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| 后端文档 | http://localhost:8000/docs |
| AI 服务 | http://localhost:8001 |

## 📖 文档

| 文档 | 说明 |
|------|------|
| [项目文档总览](docs/README.md) | 全部文档索引 |
| [AI 开发规则](docs/08_AI协作规范/AI_RULES.md) | AI Agent 必读规则 |
| [项目上下文](docs/08_AI协作规范/PROJECT_CONTEXT.md) | 项目长期上下文 |
| [AI 交接文档](docs/08_AI协作规范/AI_HANDOVER.md) | 当前阶段状态 |
| [监考系统文档](docs/04_监考系统/) | 监考功能完整设计 |
| [版本说明](VERSION.md) | 当前版本详情 |

## 🏷️ 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-08-21 | 首个稳定版本，核心功能全部完成 |

## 📌 当前版本

**v1.0.0** — 稳定版

核心功能完成度：95%（考试管理/在线考试/评分系统/AI能力/监考系统全部完成）

## 🔮 后续规划

1. 真机补充验证（iOS Safari / 微信浏览器监考测试）
2. AI 评分质量持续优化
3. RAG 知识库接入（需业务需求确认）
4. 监考增强方案评估（全屏锁定 / 原生壳）

---

<p align="center">
  <strong>© 2026 AI考试系统（企业内部版）</strong>
</p>
