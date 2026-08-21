【当前有效】

# 项目版本变更日志

> 按时间倒序排列
>
> 最后更新：2026-08-21

---

## v1.0 - 2026-08-21

**主要变化**：
- 【新增】S8.4.7 考试开始前诚信警示弹窗
  - 首次开始考试前弹出不可关闭的"考试诚信承诺提示"威慑弹窗
  - 弹窗无取消键、无关闭X，必须点击"我已知悉，开始考试"才开始考试
  - 仅首次开始弹出；断点恢复（in_progress）、已提交状态不弹
  - 移动端适配：≤480px 弹窗宽 88%、确认按钮 ≥44px 触摸目标
  - 决策背景：经评估，小窗/悬浮窗检测技术上有天花板，采用"事前威慑提示"方案替代

- 【优化】S8.4.6 监考闭环回归验证与稳定性优化
  - 刷新恢复：倒计时基于服务器时间锚点，监考经 sessionStorage 恢复
  - 切屏检测：leave/return 成对生成，快速切屏不丢事件
  - 浏览器被杀恢复：重进自动生成 leave_recovered 补偿事件
  - HR 详情：多异常组合正确产出风险等级与审核建议
  - 稳定性修复：_calculate_max_single_duration 纳入 leave_recovered
  - 稳定性修复：useMonitor 调试日志改 mlog()，MONITOR_DEBUG 开关控制

- 【修复】max_single_duration 漏算 leave_recovered 事件
- 【优化】useMonitor.js 日志开关（MONITOR_DEBUG：DEV 自动开、生产关、localStorage monitor_debug=1 临时开）

---

## v0.9 - 2026-08-21

- 【新增】S8.4.5 监考异常展示优化
  - HR 成绩详情页监考事件全部中文化+图标（monitorEventMap）
  - 风险摘要卡片新增"主要原因"结构化列表
  - 审核建议改为"💡 审核建议"标题 + 按等级描述
  - 后端 _generate_monitor_analysis 按事件类型注入中文标签
  - 后端 _generate_behavior_details 覆盖 leave_recovered / network_offline 可读描述

- 【新增】S8.4.4 考试状态恢复与监考数据持久化
  - 考试倒计时改为服务器时间锚点计算（GET /exam-records/{id}/paper 返回 started_at / server_time）
  - useMonitor.js 引入 sessionStorage 持久化（key: exam_monitor_{recordId}）
  - 浏览器被杀恢复：重新进入自动生成 leave_recovered 补偿事件
  - 提交成功后 Exam.vue 调用 monitor.clearPersistedData() 清除缓存
  - 修复 scheduleAction 合并窗口丢弃 return 事件的缺陷（MERGE_WINDOW 300ms→100ms）

---

## v0.8 - 2026-08-21

- 【新增】S8.3 事件体系增强
  - 环境采集（屏幕分辨率/网络状态/设备方向）
  - 异常标签系统（long_leave / network_offline / orientation_change）
  - 移动端兼容（touch 事件/方向变化）
  - 事件自动截断（MAX_EVENTS=100）

- 【新增】S8.2 HR 监考展示基础
  - GradingResultDetail.vue 监考详情 Tab
  - 监考事件时间线展示
  - 风险等级可视化
  - 审核建议生成

- 【新增】S8.1 监考基础能力
  - useMonitor.js监考 Hook（leave/return/network/orientation/refresh 事件）
  - 监考事件记录与存储
  - 监考基础 API 接口

---

## v0.7 - 2026-08-13

- 【新增】S7.0 HR评分复核功能
  - 顶部评分区域优化（删除客观题/AI评分卡片，新增HR复核分数输入）
  - HR复核备注功能（多行文本记录修改原因）
  - 最终成绩显示逻辑（有HR复核分数时优先显示）
  - AI评分详情折叠展示（保留原始评分数据）
  - 复核分数校验（0 <= score <= 试卷总分）
  - 数据库变更：grading_record 新增 review_score / review_comment 字段
  - API变更：PUT /api/v1/grading/results/{exam_record_id}/review

- 【优化】S7.1 启动脚本全面优化
  - start-system.bat：验证目录结构、清理旧服务、端口验证、自动打开浏览器
  - stop-system.bat：按端口精确终止进程、二次验证端口释放
  - 关键特性：--reload 自动生效、端口验证循环、失败暂停显示

- 【修复】S7.2 start-system.bat 前端启动路径

---

## v0.6 - 2026-08-12

- 【新增】S5.7-G Windows 一键启动脚本
  - start-system.bat / stop-system.bat
  - 自动启动 Backend / AI Service / Frontend
  - 端口验证与自动重试

- 【通过】S5.7-F 系统黑盒业务验收测试（23/23 项通过）
  - 管理员流程：3/3 通过
  - HR 完整业务流程：8/8 通过
  - 候选人流程：5/5 通过
  - AI 评分测试：4/4 通过
  - 异常测试：3/3 通过

---

## v0.5 - 2026-08-07

- 【新增】S5.0 AI Agent 架构
  - BaseAgent 抽象基类
  - ScoringAgent（评分 Agent）
  - ReportAgent（报告 Agent）
  - PromptLoader（YAML 版本化 Prompt）
  - LLMClient（httpx 异步调用）

- 【新增】S5.1 AI Tool 体系
  - Tool 基类与工具注册表
  - Exam 相关工具
  - 工具审计

- 【新增】S5.2 阅卷 MVP
  - AI 自动阅卷真实评分链路
  - AnswerRecord 模型扩展
  - AIScoreRecord 独立存储 AI 评分建议

- 【新增】S5.3 知识库
  - 岗位/模板/规则三级结构
  - 知识点评分
  - 评分规则版本控制

- 【新增】S5.4 评分优化
  - AI 评分 v2 Prompt（支持知识点分析）
  - 置信度机制（低置信度 <0.6 标记需人工复核）
  - AI 失败降级处理

- 【新增】S5.5 候选人分析报告
  - CandidateAnalysisReport 模型
  - AnalysisService 分析服务
  - 知识掌握度分析 / 优势薄弱点分析 / 面试建议

- 【新增】S5.6 AI评分质量优化能力检查
  - AI评分流程/质量/稳定性/数据追踪全面检查
  - B级风险项识别与优化建议

- 【修复】S5.7-D1 AI评分链路修复
  - 答案保存不完整修复
  - AI评分未自动触发修复
  - AI评分接口路径统一

---

## v0.4 - 2026-08-05

- 【新增】S4.x 企业内部功能增强
  - S4.0 MVP 稳定验收（异常处理/安全检查/Docker 部署/数据备份）
  - S4.1 用户与权限体系（用户管理/HR 权限/登录安全）
  - S4.2 固定考试模板系统（模板 CRUD/基于模板创建考试）
  - S4.3 考试发布管理（发布/时间设置/参与情况管理）
  - S4.4 HR 考试数据分析（考试人数/平均分/通过率/员工历史）
  - S4.5 AI 考试分析增强（整体总结/常见错误/培训建议）

---

## v0.3 - 2026-08初

- 【新增】S3.x 考试参与与评分
  - S3.1 候选人考试流程后端
  - S3.2 候选人考试前端
  - S3.3 评分与报告（客观评分/AI评分/AI报告）
    - S3.3.1 评分基础架构
    - S3.3.2 客观题自动评分
    - S3.3.3 基础评分结果查询
    - S3.3.4 AI-Service 调用链路
    - S3.3.5 主观题 AI 评分集成
    - S3.3.6 AI 考试分析报告
  - S3.4 日志体系完善

---

## v0.2 - 2026-08初

- 【新增】S2.x 考试资源管理
  - 用户认证（JWT）
  - 权限保护
  - 考试 CRUD
  - 题目管理
  - JSON 导入
  - HR 前端页面

---

## v0.1 - 2026-08初

- 【新增】S1.x 基础设施
  - 数据库设计（核心表）
  - ORM 模型
  - 数据库迁移（Alembic）
  - 统一异常处理
  - 统一响应格式
  - 密码安全（bcrypt）

- 【新增】项目初始化
  - 项目目录结构搭建
  - 前后端骨架
  - AI 服务骨架

---

# 版本统计

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0 | 2026-08-21 | 诚信弹窗 + 监考闭环验证 |
| v0.9 | 2026-08-21 | 监考异常展示 + 数据持久化 |
| v0.8 | 2026-08-21 | 监考事件体系 + HR展示 |
| v0.7 | 2026-08-13 | HR复核 + 启动优化 |
| v0.6 | 2026-08-12 | 一键启动 + 黑盒验收 |
| v0.5 | 2026-08-07 | AI Agent + 评分增强 |
| v0.4 | 2026-08-05 | 企业内部功能增强 |
| v0.3 | 2026-08初 | 考试参与与评分 |
| v0.2 | 2026-08初 | 考试资源管理 |
| v0.1 | 2026-08初 | 基础设施 + 项目初始化 |