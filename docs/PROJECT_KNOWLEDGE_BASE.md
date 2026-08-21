【当前有效】

# AI 开发知识库

> **本文档为 AI 后续开发唯一上下文入口。新 AI 接手开发时，必须首先阅读此文件。**
>
> 最后更新：2026-08-21

---

# 1. 项目背景

## 项目概述
- **项目名称**：AI考试系统（企业内部版）
- **服务对象**：企业人事部门
- **核心价值**：AI 智能考试与测评，替代人工批改，效率提升 80%+

## 当前架构
- **架构模式**：三服务架构
- **前端**：Vue3 + Vite + Element Plus
- **后端**：FastAPI + SQLAlchemy 2.0
- **AI 服务**：FastAPI + httpx + DeepSeek
- **数据库**：MySQL 8.0

```
Frontend (Vue3:3000) → Backend (FastAPI:8000) → MySQL 8.0
                              ↓ HTTP
                         AI Service (FastAPI:8001)
```

---

# 2. 关键文件清单（按重要性排序）

## 前端核心
| 文件 | 用途 | 重要性 |
|------|------|--------|
| `frontend/src/views/exam/Exam.vue` | 考试页（答题/监考/诚信弹窗） | ⭐⭐⭐ |
| `frontend/src/views/admin/grading/GradingResultDetail.vue` | 监考详情（HR查看监考事件） | ⭐⭐⭐ |
| `frontend/src/hooks/useMonitor.js` | 监考 Hook（事件检测/持久化/恢复） | ⭐⭐⭐ |
| `frontend/src/api/examRecord.js` | 考试记录 API | ⭐⭐ |
| `frontend/src/api/gradingResult.js` | 评分结果 API | ⭐⭐ |
| `frontend/src/stores/exam.js` | 考试状态 Store | ⭐⭐ |

## 后端核心
| 文件 | 用途 | 重要性 |
|------|------|--------|
| `backend/app/services/exam_record_service.py` | 考试记录+监考分析 | ⭐⭐⭐ |
| `backend/app/services/grading_service.py` | 评分+监考详情 | ⭐⭐⭐ |
| `backend/app/services/exam_service.py` | 考试 CRUD | ⭐⭐⭐ |
| `backend/app/services/ai_scoring_service.py` | AI 评分服务 | ⭐⭐ |
| `backend/app/services/ai_report_service.py` | AI 报告服务 | ⭐⭐ |
| `backend/app/models/exam_record.py` | 考试记录模型（含监考数据） | ⭐⭐ |

## AI 核心
| 文件 | 用途 | 重要性 |
|------|------|--------|
| `ai-service/app/agents/scoring_agent.py` | 评分 Agent | ⭐⭐⭐ |
| `ai-service/app/agents/report_agent.py` | 报告 Agent | ⭐⭐⭐ |
| `ai-service/app/prompts/scoring/v3.yaml` | 最新评分 Prompt | ⭐⭐⭐ |
| `ai-service/app/llm/client.py` | LLM 客户端 | ⭐⭐ |
| `ai-service/app/tools/exam_tools.py` | 考试相关工具 | ⭐⭐ |

---

# 3. 重要规则（必须遵守）

## 核心规则
1. **AI_RULES.md 中的所有规则**（技术栈/架构/安全/AI功能）
2. **考试流程不得随意修改**（核心流程已稳定）
3. **监考数据持久化逻辑不得随意修改**（sessionStorage 键名格式固定）
4. **数据库变更必须通过 Alembic**（禁止直接修改数据库）
5. **密码必须 bcrypt 哈希**（禁止明文存储）
6. **JWT 密钥必须使用环境变量**（禁止硬编码）
7. **前端页面不得直接调用 axios**（必须通过 API 封装模块）
8. **AI Prompt 必须版本化**（修改时创建新版本）

---

# 4. 禁止修改项

## 绝对禁止
- **数据库结构**（除非有明确需求文档）
- **考试核心流程**（已通过黑盒测试验证）
- **AI 评分逻辑**（除非有 Prompt 版本升级）
- **监考算法核心逻辑**（已通过闭环回归验证）

## 限制修改
- 监考事件定义（需同步更新前后端）
- 考试状态机（not_started → in_progress → submitted → graded）
- API 路径（需同步更新前端 API 模块）

---

# 5. 后续开发规范

## 开发前必读
1. 阅读 `docs/08_AI协作规范/AI_RULES.md` 和本文件
2. 阅读相关 S 阶段记录（`docs/05_开发记录/`）
3. 理解现有代码后再开发

## 开发原则
1. **最小化修改原则**：只修改必要的代码
2. **同步更新文档**：修改后必须同步更新 change-log.md 和 AI_HANDOVER.md
3. **保持向后兼容**：新增功能不得破坏现有功能
4. **充分测试**：修改后必须进行回归测试

## 开发后同步
- `docs/PROJECT_CHANGELOG.md` — 记录变更
- `docs/08_AI协作规范/AI_HANDOVER.md` — 更新状态

---

# 6. 常见开发场景指南

## 场景 1：修改考试流程
1. 阅读 `docs/03_业务设计/考试流程设计.md`
2. 阅读 `Exam.vue` 和 `exam_record_service.py`
3. 理解现有状态机后再修改

## 场景 2：修改监考功能
1. 阅读 `docs/04_监考系统/` 全部文档
2. 阅读 `useMonitor.js` 和 `exam_record_service.py` 中的监考分析
3. 在 GradingResultDetail.vue 中验证 HR 展示

## 场景 3：修改 AI 评分
1. 阅读 `docs/03_业务设计/AI评分机制说明.md`
2. 阅读 `ScoringAgent` 和 `v3.yaml` Prompt
3. Prompt 修改时创建新版本（v4.yaml）
4. 同步更新评分元信息中的 prompt_version

## 场景 4：新增数据库字段
1. 创建 Alembic 迁移文件
2. 更新 ORM 模型
3. 更新 Pydantic Schema
4. 更新相关 Service 方法
5. 更新 API 端点

---

# 7. 快速参考

## 端口
| 服务 | 端口 |
|------|------|
| Frontend | 3000 |
| Backend | 8000 |
| AI Service | 8001 |
| MySQL | 3306 |

## 一键启动
```bash
# Windows: 双击 start-system.bat
```

## 测试账号
- HR: admin / 密码见 backend/.env
- 候选人: 姓名+手机+考试码

## 关键 API
| 功能 | 方法 | 路径 |
|------|------|------|
| 考试答题 | GET | /api/v1/exam-records/{id}/paper |
| 提交考试 | POST | /api/v1/exam-records/{id}/submit |
| 评分结果 | GET | /api/v1/grading/results |
| HR 复核 | PUT | /api/v1/grading/results/{id}/review |
| AI 评分 | POST | /api/v1/ai-scoring/evaluate |

---

# 8. 关联文档

## AI 协作规范
- [AI_RULES.md](08_AI协作规范/AI_RULES.md) — 开发规则【必读】
- [AI_HANDOVER.md](08_AI协作规范/AI_HANDOVER.md) — 当前状态
- [PROJECT_CONTEXT.md](08_AI协作规范/PROJECT_CONTEXT.md) — 项目上下文

## 核心设计
- [考试流程设计](03_业务设计/考试流程设计.md)
- [监考功能设计](04_监考系统/监考功能设计.md)
- [AI评分机制说明](03_业务设计/AI评分机制说明.md)

## 阶段记录
- [S8阶段记录](05_开发记录/S8阶段记录.md) — 监考全阶段【核心】
- [S7阶段记录](05_开发记录/S7阶段记录.md) — HR评分/启动优化

## 交付文档
- [PROJECT_FINAL_STATUS.md](PROJECT_FINAL_STATUS.md) — 项目最终状态
- [PROJECT_CHANGELOG.md](PROJECT_CHANGELOG.md) — 版本变更日志