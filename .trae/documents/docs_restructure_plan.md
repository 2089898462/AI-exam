# AI考试系统项目文档整理与归档实施计划

## 调研结论

### 现有文档现状
- `docs/` 下有 18 个文件，包含 `AI_RULES.md`、`PROJECT_CONTEXT.md`、`AI_HANDOVER.md`、`PRD.md`、`architecture.md`、`database.md`、`api.md`、`ai-design.md`、`change-log.md`、`test-plan.md` 等
- `change-log.md` 已记录 S7.2-S8.4.7 全部阶段变更（27+ 条目）
- `PROJECT_CONTEXT.md` 的阶段路线仍停留在 S4 规划中，未同步 S5-S8 进展
- `AI_HANDOVER.md` 已更新至 S8.4.7
- 存在重复：`PROJECT_CONTEXT.md` 与 `project-context.md` 两个文件内容相似
- 存在版本漂移：部分设计文档（PRD/api/database/architecture）仍反映 MVP 状态，需与当前实现对齐

### 代码架构现状
- **前端**：Vue3 + Vite + Element Plus + Pinia + Vue Router
  - 关键页面：Exam.vue、GradingResultDetail.vue
  - 关键 Hooks：useMonitor.js、useAutoSave.js
  - API 封装：api/*.js
  - Store：stores/exam.js、stores/user.js
- **后端**：FastAPI + SQLAlchemy 2.0 + Alembic
  - 分层：api/v1/endpoints → schemas → services → models → db
  - 核心模块：exam_service、grading_service、exam_record_service、ai_scoring_service 等
  - 16+ 数据模型
- **AI 服务**：独立 FastAPI 服务
  - Agent：ScoringAgent、ReportAgent、ConversationAgent
  - Prompt：YAML 版本化管理（scoring v1-v3、report v1、analysis v1、agent v1）
  - LLM：DeepSeek 通过兼容接口

### 监考系统现状（S8 阶段核心）
- useMonitor.js：完整事件监听体系（visibilitychange/blur/focus/pagehide/pageshow/orientation_change/network_change）
- sessionStorage 持久化：key = exam_monitor_{recordId}
- leave_recovered 补偿：浏览器被杀后恢复
- 后端 risk_level 计算：normal/low/medium/high
- HR 端展示：事件中文映射 + 风险摘要 + 审核建议 + 时间线

## 文档目录结构（待生成）

```
docs/
├── README.md                          ← 新：文档索引
├── 01_项目概览/
│   ├── 项目介绍.md                    ← 新：项目定位、目标、价值
│   ├── 产品定位.md                    ← 新：用户角色、业务场景
│   └── 功能清单.md                    ← 新：当前能力完整清单
├── 02_技术架构/
│   ├── 系统架构设计.md                ← 重写：基于 architecture.md + PROJECT_CONTEXT.md
│   ├── 前后端架构.md                  ← 新：前端/后端分层、目录、关键模块
│   ├── AI服务架构.md                  ← 重写：基于 ai-design.md + ai-service 源码
│   └── 数据库设计说明.md              ← 重写：基于 database.md + 实际模型
├── 03_业务设计/
│   ├── 考试流程设计.md                ← 新：完整考试生命周期
│   ├── 题库管理设计.md                ← 新：考试创建/模板/导入
│   ├── 评分流程设计.md                ← 新：客观+AI混合评分
│   └── AI评分机制说明.md              ← 新：Agent/Prompt/数据流
├── 04_监考系统/
│   ├── 监考功能设计.md                ← 新：监考整体方案
│   ├── 监考事件体系.md                ← 新：全部事件定义与触发条件
│   ├── 监考数据流程.md                ← 新：数据流端到端
│   └── 异常分析规则.md                ← 新：风险等级计算规则
├── 05_开发记录/
│   ├── S1-S3阶段记录.md               ← 新：基础/资源/评分
│   ├── S4阶段记录.md                  ← 新：MVP稳定/模板/考试/报告
│   ├── S5阶段记录.md                  ← 新：AI Agent/评分增强
│   ├── S6阶段记录.md                  ← 新：AI评分/报告集成
│   ├── S7阶段记录.md                  ← 新：HR评分/考试增强
│   └── S8阶段记录.md                  ← 新：监考全阶段（8.1-8.4.7）
├── 06_测试记录/
│   ├── 功能测试报告.md                ← 新：基于现有测试
│   ├── 稳定性测试报告.md              ← 新：基于 S8.4.6 回归
│   └── 已知问题列表.md                ← 新：当前限制
├── 07_部署维护/
│   ├── 本地运行说明.md                ← 新：Windows 本地运行
│   ├── 环境配置说明.md                ← 新：环境变量/端口
│   ├── 数据备份恢复.md                ← 新：MySQL 备份
│   └── 常见问题.md                    ← 新：FAQ
├── 08_AI协作规范/
│   ├── AI_RULES.md                    ← 保留：当前有效
│   ├── PROJECT_CONTEXT.md             ← 保留：需更新
│   └── AI_HANDOVER.md                 ← 保留：当前有效
├── PROJECT_FINAL_STATUS.md            ← 新：项目最终状态
├── PROJECT_CHANGELOG.md               ← 新：按时间排序的版本日志
└── PROJECT_KNOWLEDGE_BASE.md           ← 新：AI 后续开发唯一入口
```

## 实施步骤

### 1. 准备工作（当前）
- 调研项目结构 ✅
- 收集现有文档内容 ✅
- 创建文档目录结构

### 2. 生成 01_项目概览（3 个文件）
- 基于 AI_RULES.md、PROJECT_CONTEXT.md、PRD.md
- 整理项目定位、用户角色、功能清单

### 3. 生成 02_技术架构（4 个文件）
- 基于 architecture.md、ai-design.md、database.md + 代码结构
- 补充当前实际实现的架构细节

### 4. 生成 03_业务设计（4 个文件）
- 基于 PRD.md + 代码中的业务流程
- 整理考试流程、题库管理、评分流程、AI 评分机制

### 5. 生成 04_监考系统（4 个文件）
- 基于 useMonitor.js、exam_record_service.py、grading_service.py
- 整理事件体系、数据流、异常分析规则

### 6. 生成 05_开发记录（6 个文件）
- 基于 change-log.md + AI_HANDOVER.md
- 每个阶段统一格式：目标/完成功能/修改文件/技术方案/测试结果/遗留问题/当前状态

### 7. 生成 06_测试记录（3 个文件）
- 基于 test-plan.md + S8.4.6 回归测试报告
- 整理功能测试、稳定性测试、已知问题

### 8. 生成 07_部署维护（4 个文件）
- 基于 README.md + start-system.bat + docker/ 目录
- 整理本地运行、环境配置、数据备份、常见问题

### 9. 生成 08_AI协作规范
- 复制 AI_RULES.md、PROJECT_CONTEXT.md、AI_HANDOVER.md 到此目录
- 更新 PROJECT_CONTEXT.md 中的阶段信息

### 10. 生成最终交付文档（3 个文件）
- PROJECT_FINAL_STATUS.md：项目状态总览
- PROJECT_CHANGELOG.md：版本日志
- PROJECT_KNOWLEDGE_BASE.md：AI 开发唯一入口

### 11. 生成 README.md
- 文档索引，指向各目录

## 关键考虑

1. **保留历史**：不删除旧文档，新增结构化目录。旧文档保留在原位作为历史参考。
2. **标注版本**：每个文档标注 `【当前有效】`/`【历史方案】`/`【已废弃】`
3. **以代码为准**：文档内容以当前代码实现为准，旧方案明确标注为历史
4. **移动端适配**：监考系统文档需包含移动端相关设计说明
5. **安全性**：AI 数据分级规则、安全规则必须保留在文档中

## 验证方式
- 生成的文档与代码实现一致性检查
- 新 AI 工程师可读可理解性检查
- 文档交叉引用完整性检查
