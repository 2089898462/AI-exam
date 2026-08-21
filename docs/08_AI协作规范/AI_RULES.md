【当前有效】

# AI 项目开发规则（摘要版）

> **本文件为 AI Agent 开发时必须遵守的长期规则摘要。完整规则见 docs/AI_RULES.md**
>
> 创建日期：2026-08-05
> 最后更新：2026-08-21（摘要版整理）

---

# 1. 项目业务定位

- **项目名称**：AI考试系统（企业内部版）
- **核心定位**：企业内部 AI 智能考试与测评系统，服务于企业人事部门
- **核心流程**：HR 创建考试 → 发布考试 → 员工参加考试 → 自动评分 → AI 生成分析报告 → HR 查看结果

# 2. 用户角色

- **管理员**：系统维护、用户管理
- **HR（核心角色）**：创建考试、管理考试、查看成绩、查看 AI 报告
- **员工**：参加考试、查看个人成绩
- **禁止**：部门主管、多级审核、候选人（Candidate）角色

# 3. 技术栈约束

| 层 | 技术 |
|----|------|
| 前端 | Vue3 + Vite + Element Plus + Pinia + Vue Router + Axios |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic |
| 数据库 | MySQL 8.0（InnoDB / utf8mb4） |
| AI服务 | FastAPI + httpx + DeepSeek |

# 4. 架构约束

- **后端分层**：API → Schema → Service → Model → Database
- **前端分层**：页面 → 组件 → Store → API封装
- **API 层禁止直接操作数据库**
- **页面禁止直接调用 axios**
- **统一响应格式**：ApiResponse（success/error/created）
- **统一异常处理**：AppException 体系

# 5. 数据库规范

- 必备字段：created_at / updated_at
- 必须通过 Alembic migration 修改
- 表名：小写+下划线，主键：id BIGINT AUTO_INCREMENT
- 外键：{目标表名}_id

# 6. AI 功能规则

- Prompt 必须版本化（v1.yaml、v2.yaml）
- AI Agent 必须继承 BaseAgent
- JSON 解析必须健壮（支持多种格式）
- AI 数据分级访问（L1禁止/L2脱敏/L3授权/L4允许）
- AI 调用必须通过 Backend 鉴权

# 7. 安全规则

- 密码必须 bcrypt 哈希
- 密钥必须使用环境变量
- 禁止明文存储密码
- 禁止在日志中记录敏感信息

# 8. 禁止事项

- 禁止未经确认重构已有模块
- 禁止重复创建已有功能
- 禁止提前开发未规划模块
- 禁止引入未经确认的技术
- MVP 阶段禁止：RAG、复杂 Agent 编排、AI 监考、随机组卷

# 9. 文档维护

开发完成后必须同步：
- docs/change-log.md
- docs/AI_HANDOVER.md
- docs/PROJECT_CONTEXT.md

---

> **完整规则请参阅：[AI_RULES.md](../AI_RULES.md)**