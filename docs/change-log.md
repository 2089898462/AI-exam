# 项目技术变更记录

> **本文件记录项目重大技术变更索引，不记录详细开发过程。**
>
> 最后更新：2026-08-21

# S8.4.7 考试开始前诚信警示弹窗

**时间**：2026-08-21
**版本**：S8.4.7
**结果**：✅ 完成

**变更内容**：
首次开始考试（not_started）前弹出不可关闭的"考试诚信承诺提示"威慑弹窗，考生必须点击"我已知悉，开始考试"后考试才真正开始：
1. 文案告知：全程智能监考监测、禁止切屏/锁屏/离开页面、禁止小窗/分屏/悬浮窗及搜索 AI 工具查答案、切屏行为自动记录并提交人工审核、需独立作答；
2. 弹窗不可关闭（无取消键/无右上角X/ESC无效/点遮罩无效），杜绝跳过；
3. 仅首次开始考试弹出；断点恢复（in_progress）与已提交状态不弹；
4. 移动端适配：≤480px 弹窗宽度 88%、确认按钮触摸目标 ≥44px。

**修改文件**：
| 文件 | 说明 |
|------|------|
| `frontend/src/views/exam/Exam.vue` | loadPaper not_started 分支前置 ElMessageBox 警示弹窗；末尾新增弹窗移动端全局样式 |

**兼容性**：无 API/数据库/考试流程变更；弹窗 await 在 try 块内，与既有错误处理链路一致。

# S8.4.6 监考闭环回归验证与稳定性优化

**时间**：2026-08-21
**版本**：S8.4.6
**结果**：✅ 完成（回归验证通过 + 2 处修复）

**变更内容**：
监考功能全链路闭环回归验证（S8.4.4 状态恢复 + S8.4.5 HR 展示）及稳定性优化，不新增功能：
1. **修复** `exam_record_service._calculate_max_single_duration` 漏算 `leave_recovered` 事件的缺陷：S8.4.4 异常中断补偿事件携带真实离开时长，原逻辑仅统计 `exam_leave`，导致该场景下单次最长离开时长被低估（`long_leave` 标签漏报）；
2. **日志优化** `useMonitor.js`：新增 `MONITOR_DEBUG` 开关与 `mlog()` 函数，全部调试日志（`console.log('[Monitor]'`）改经开关输出——开发环境自动开启、生产环境关闭（可通过 `localStorage.setItem('monitor_debug','1')` 临时开启）；`console.warn/error` 关键错误日志无条件保留；
3. **回归验证通过**：刷新恢复/切屏检测/浏览器被杀恢复（leave_recovered 补偿）/HR 详情展示/历史数据兼容/提交后缓存清理/多标签页隔离/MAX_EVENTS 限制，详见《S8.4.6 回归测试报告》。

**修改文件**：
| 文件 | 说明 |
|------|------|
| `backend/app/services/exam_record_service.py` | `_calculate_max_single_duration` 纳入 leave_recovered 事件时长 |
| `frontend/src/hooks/useMonitor.js` | MONITOR_DEBUG 开关 + mlog() 替换全部调试日志 |

**兼容性**：无数据库/API/考试流程变更；Node 端到端逻辑测试（真实源码打包运行）18/18 通过，后端风险分析单测 8/8 通过，旧格式数据（无 duration 字段）容错正常。

# S8.4.5 监考异常展示优化

**时间**：2026-08-21
**版本**：S8.4.5
**结果**：✅ 完成

**变更内容**：
HR 端监考详情从"技术事件展示"升级为"HR 可理解的异常分析展示"：
1. 前端新增 `monitorEventMap` 事件中文映射（label/icon/type），时间线显示"🔄 异常中断恢复"等中文+图标，未知事件兜底显示"其他监考事件"（不显示 undefined/原始英文名）；
2. 时间线每条事件增加详情说明（`eventDescription`：按类型生成如"浏览器后台恢复，离开60秒"）；
3. 风险摘要卡片新增"主要原因"结构化列表（离开概况/超5分钟离开/网络关联/异常恢复/高频切换/刷新尝试，兜底 risk_reason）；
4. 审核建议改为"💡 审核建议"标题 + 描述文案，按风险等级生成（normal/low/medium/high）；
5. 后端 `_generate_monitor_analysis` 按事件类型注入中文行为标签（异常中断恢复/网络异常/设备方向变化），`_generate_behavior_details` 覆盖 leave_recovered/network_offline/orientation_change/refresh_attempt 事件的可读描述。

**修改文件**：
| 文件 | 说明 |
|------|------|
| `frontend/src/views/admin/grading/GradingResultDetail.vue` | monitorEventMap / eventDescription / riskReasonList / 审核建议样式 |
| `backend/app/services/grading_service.py` | 事件驱动中文标签注入、行为详情扩展、审核建议文案对齐 |

**兼容性**：纯展示层与分析层增强，无数据库/API 结构变更；历史考试（无 analysis/events 字段）正常兜底显示。

# S8.4.4 考试状态恢复与监考数据持久化修复

**时间**：2026-08-21
**版本**：S8.4.4
**结果**：✅ 完成

**问题描述**：
S8.4 监考增强后出现回归：刷新考试页面倒计时重新开始；手机切出浏览器再返回倒计时重置；页面重新加载后监考事件全部丢失；切屏 leave/return 事件无法稳定记录。

**根因**：
1. 倒计时基于 `Date.now()` 页面加载时刻初始化，无服务器时间基准，刷新即重置（`started_at` 数据库有值但 `/paper` 接口不返回）；
2. useMonitor.js 监考数据仅存于 Vue 内存 ref，页面刷新/浏览器回收即全部丢失；
3. S8.3.4.x 的 `scheduleAction` 合并窗口在 leave pending 期间收到 return 时直接丢弃 return 事件，导致单会话内切屏检测失效（S8.4.3-d 已修复）。

**修复方案**：
1. `ExamPaperResponse` 新增 `started_at`/`server_time` 字段，前端以「开始时间 + 总时长 - 服务器当前时间（经时钟偏差校准）」计算真实剩余时间，刷新/切后台恢复且防系统时间篡改；
2. useMonitor.js 引入 sessionStorage 持久化（key: `exam_monitor_{recordId}`），事件变化实时写入，`startMonitoring` 恢复历史数据而非清零；上次会话在隐藏状态被终止时生成 `leave_recovered` 补偿事件；提交成功后由 Exam.vue 调用 `clearPersistedData` 清除缓存。

**修改文件**：
| 文件 | 说明 |
|------|------|
| `backend/app/schemas/exam_record.py` | L154-156 ExamPaperResponse 新增 started_at / server_time |
| `backend/app/api/v1/endpoints/exam_records.py` | L166-168 /paper 接口返回两字段 |
| `frontend/src/views/exam/Exam.vue` | 倒计时重构为服务器时间锚点计算；切后台返回立即校准；startMonitoring 传 recordId；提交成功清除监考缓存 |
| `frontend/src/hooks/useMonitor.js` | sessionStorage 持久化/恢复/补偿/清除；全事件点接入 persistData |

**兼容性**：新增字段均为可选，旧考试记录正常访问；无数据库结构变更，无需 Alembic 迁移。

**注意事项**：后端服务需重启才能生效（开发服务器未开 --reload 时）。

# S7.2 start-system.bat 前端启动路径修复

**时间**：2026-08-13
**版本**：S7.2
**结果**：✅ 完成

**问题描述**：
start-system.bat 启动时 Backend 和 AI Service 正常，但 Frontend 启动失败。手动在 frontend 目录执行 `npm run dev` 可以正常启动。

**根因**：
`start` 命令打开新 CMD 窗口时，新窗口的工作目录继承自父进程，而非 `pushd` 切换的目录。导致新窗口在错误目录（如 `C:\Windows\System32`）下执行 `npm run dev`，找不到 `package.json`。

**修复方案**：
使用 `start` 命令的 `/d` 参数显式指定新窗口的工作目录：

```bat
# 修复前
pushd "%BASEDIR%frontend"
start "AI-Exam Frontend" cmd /k "npm run dev"
popd

# 修复后
pushd "%BASEDIR%frontend"
start "AI-Exam Frontend" /d "%BASEDIR%frontend" cmd /k "npm run dev"
popd
```

**修改文件**：
| 文件 | 修改行 | 说明 |
|------|--------|------|
| `start-system.bat` | L64 | Backend: 添加 `/d "%BASEDIR%backend"` |
| `start-system.bat` | L88 | AI Service: 添加 `/d "%BASEDIR%ai-service"` |
| `start-system.bat` | L122 | Frontend: 添加 `/d "%BASEDIR%frontend"` |

**测试结果**：
- ✅ 端口 8000 (Backend) 正常
- ✅ 端口 8001 (AI Service) 正常
- ✅ 端口 3000 (Frontend) 正常
- ✅ Frontend 可在 http://localhost:3000 访问

---

# S7.0 HR评分复核功能

**时间**：2026-08-13
**版本**：S7.0
**结果**：✅ 完成

**开发目标**：
将AI自动评分结果页面优化为「AI评分 + HR人工复核」模式，支持HR手动调整分数并添加复核备注。

**新增功能**：
1. ✅ 顶部评分区域优化：删除客观题/AI评分卡片，保留系统总分，新增HR复核分数输入
2. ✅ HR复核备注功能：支持多行文本记录修改原因
3. ✅ 最终成绩显示逻辑：有HR复核分数时优先显示复核分数
4. ✅ AI评分详情折叠展示：保留AI原始评分数据，支持展开查看
5. ✅ 复核分数校验：分数范围校验（0 <= score <= 试卷总分）

**修改文件**：

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/grading_record.py` | 修改 | 新增 review_score、review_comment 字段 |
| `backend/app/schemas/grading.py` | 修改 | 新增 HRReviewUpdateRequest Schema，更新 GradingResultDetailResponse |
| `backend/app/services/grading_service.py` | 修改 | 新增 update_hr_review 方法，分数校验逻辑 |
| `backend/app/api/v1/endpoints/grading_results.py` | 修改 | 新增 PUT /results/{exam_record_id}/review 接口 |
| `backend/alembic/versions/f1a2b3c4d5e6_add_hr_review_fields.py` | 新建 | Alembic 迁移文件 |
| `frontend/src/api/gradingResult.js` | 修改 | 新增 updateHRReview 方法 |
| `frontend/src/views/admin/grading/GradingResultDetail.vue` | 修改 | 页面重构，新增复核功能 |

**数据库变更**：
```sql
ALTER TABLE grading_record ADD COLUMN review_score NUMERIC(8,2) NULL COMMENT 'HR复核分数';
ALTER TABLE grading_record ADD COLUMN review_comment TEXT NULL COMMENT 'HR复核备注';
```

**API变更**：
- 新增 `PUT /api/v1/grading/results/{exam_record_id}/review`
- 请求体：`{ "review_score": float, "review_comment": string }`
- 权限：HR/Admin

**显示逻辑**：
- 最终成绩 = review_score（如果存在） || total_score（系统总分）
- 原AI评分数据（auto_score、ai_score）保留不变

---

# S7.1 启动脚本全面优化

**时间**：2026-08-13
**版本**：S7.1
**结果**：✅ 完成

**优化目标**：
重新设计启动/关闭脚本，确保开发环境稳定可靠，解决旧脚本存在的启动后代码不生效、无法发现启动失败、端口清理不完全等问题。

**优化内容**：

| # | 问题 | 优化方案 |
|---|------|----------|
| 1 | 后端代码修改后仍运行旧版本 | 所有 uvicorn 启动增加 `--reload` 参数 |
| 2 | 服务启动失败无法发现 | 新增端口监听检查机制，每个服务启动后验证端口是否就绪，超时30秒则报错并暂停 |
| 3 | 端口清理不完全 | 按端口精确清理，增加 `netstat` 二次验证 |
| 4 | 路径兼容问题 | 使用 `%~dp0` 获取脚本所在目录，支持任意电脑路径运行 |
| 5 | bat 中文乱码 | 增加 `chcp 65001 >nul` 切换到 UTF-8 编码页 |
| 6 | 启动完成提示不代表服务可用 | 新增端口验证循环，确认服务真实监听后才标记成功 |
| 7 | 前端依赖未安装自动检测 | 启动前检查 `node_modules` 是否存在，不存在则自动执行 `npm install` |

**修改文件**：
| 文件 | 操作 | 说明 |
|------|------|------|
| `start-system.bat` | 重写 | 6步启动流程，含端口验证、错误处理、--reload |
| `stop-system.bat` | 重写 | 3步关闭流程，含二次验证、进程计数 |

**启动流程**：
1. 验证目录结构（backend/ai-service/frontend）
2. 清理旧服务（按端口精确清理 + 关闭AI-Exam窗口）
3. 启动 Backend（--reload，30秒超时检测）
4. 启动 AI Service（--reload，30秒超时检测）
5. 启动 Frontend（自动检测 node_modules，40秒超时检测）
6. 输出访问地址，5秒后自动打开浏览器

**关闭流程**：
1. 按端口（8000/8001/3000）精确终止进程
2. 关闭 AI-Exam 标题窗口
3. 等待3秒后二次验证端口是否已释放

**测试结果**：
- ✅ stop-system.bat：成功关闭3个服务
- ✅ start-system.bat：3个服务正常启动
- ✅ --reload 生效：后端代码修改后接口立即生效
- ✅ Swagger 文档：http://localhost:8000/docs 正常访问
- ✅ 前端页面：http://localhost:3000 正常访问

---

# S5.7-G Windows一键启动脚本

**时间**：2026-08-12
**版本**：S5.7-G
**结果**：✅ 完成

**新增文件**：
1. `start-system.bat` - 一键启动脚本
2. `stop-system.bat` - 一键关闭脚本

**脚本功能**：
- start-system.bat：
  - 自动检查Python和Node.js运行环境
  - 自动清理占用端口（8000/8001/3000）
  - 启动Backend服务（端口8000）
  - 启动AI Service服务（端口8001）
  - 启动Frontend服务（端口3000）
  - 自动打开浏览器访问系统
  - 每个服务独立窗口运行，窗口标题明确
  
- stop-system.bat：
  - 确认后关闭所有服务
  - 通过端口号精确定位进程
  - 不影响其他无关程序

**使用方式**：
- 启动：双击 `start-system.bat`
- 关闭：双击 `stop-system.bat`

**访问地址**：
- Backend: http://localhost:8000
- AI Service: http://localhost:8001
- Frontend: http://localhost:3000
- 登录页: http://localhost:3000/login

**注意事项**：
- 需确保backend/.env和ai-service/.env配置正确
- 首次使用需确保前端依赖已安装（npm install）
- 数据库使用SQLite，无需单独启动

---

# S5.7-F 系统黑盒业务验收测试

**时间**：2026-08-07
**版本**：S5.7-F
**结果**：✅ 通过（23/23 项通过）

**测试范围**：黑盒测试方式验证管理员/HR/候选人全流程业务 + 异常处理

**关键验证**：
- 管理员登录、权限验证
- HR 创建考试、添加题目（单选/判断/简答）、发布考试
- 候选人通过考试码进入考试、答题、提交
- AI 自动评分，返回 score/reason/confidence
- 异常处理：错误考试码、重复参加均被正确拦截

**修复记录**：
1. **P1: exam_code 未自动生成**
   - 文件：`backend/app/services/exam_service.py`
   - 添加 `_generate_exam_code()` 方法，创建考试时自动生成唯一考试码
   - 格式：`EXAM-{时间戳}-{UUID前8位}`

2. **配置兼容问题**
   - 文件：`backend/app/core/config.py`
   - 添加 `extra = "ignore"` 配置，解决环境变量冲突

**验收脚本**：`ai-service/run_blackbox_test.py`

---

# S5.7-E AI阅卷完整业务验收

**时间**：2026-08-07
**版本**：S5.7-E
**结果**：✅ 通过

**验收范围**：完整考试业务链路（HR创建→候选人答题→AI评分→HR查看成绩）

**关键验证**：
- 考试创建、题目管理（单选/判断/简答）、考试发布
- 候选人通过考试码进入、答题、提交
- AI 自动评分（deepseek-chat），3秒完成
- 评分结果正确写入数据库（ExamRecord/AnswerRecord/GradingRecord）
- HR 可查询考试成绩

**发现问题**（非阻塞）：
1. 防重复参加未生效：同一候选人可创建多条考试记录
2. HR 成绩查看接口 total_records 返回 0

**验收脚本**：`ai-service/run_acceptance_test.py`

---

# S5.7-D1.5-D DeepSeek真实调用自动化验证

---

# S5.6 AI评分质量优化能力检查

**时间**：2026-08-06

**版本**：S5.6

**检查目标**：检查当前AI评分能力是否满足实际招聘考试使用要求

**检查内容**：

1. AI评分流程检查
   - 候选人提交→简答题识别→AI评分调用→评分结果解析→结果保存→HR查看
   - 确认流程完整性、AI失败影响、重新评分支持

2. AI评分Prompt质量检查
   - v1/v2 Prompt模板分析
   - 检查角色定义、评分目标、题目信息、标准答案、评分规则、输出格式约束

3. 评分规则体系检查
   - 知识库三级结构（岗位→模板→规则）
   - 知识点评分、扣分规则、满分条件支持

4. AI评分稳定性检查
   - temperature配置、置信度机制、输出格式稳定性

5. AI评分结果数据检查
   - AIScoreRecord记录内容完整性
   - 后续人工复核和历史追踪支持

6. 人工复核机制检查
   - HR查看/确认/拒绝AI评分流程
   - AI评分不直接替代最终成绩

7. AI调用成本与性能检查
   - 单题调用vs批量调用分析
   - Token消耗优化建议

**检查结果**：

✅ **通过** - AI评分能力满足真实招聘考试使用要求

**风险清单**：

| 编号 | 问题 | 等级 | 影响 | 建议 |
|------|------|------|------|------|
| B001 | 单次评分token消耗较高 | B | 影响AI调用成本 | 建议实现批量评分接口 |
| B002 | 缺少评分结果二次校验机制 | B | 影响评分准确性 | 建议增加分数与置信度矛盾检查 |
| B003 | AI评分结果缺少评分范围限制校验 | B | 影响数据一致性 | 建议增加分数合理性校验 |

**优化建议**：

1. 增加批量评分接口，减少多次HTTP调用成本
2. 增加评分结果合理性校验逻辑
3. 增加评分标准分级配置能力
4. 考虑增加评分结果缓存和复用机制

**检查结论**：系统可进入S6正式业务优化阶段，但建议优先处理B级风险项

---

# S5-B AI 自动阅卷真实评分链路建设

**时间**：2026-08-06

**版本**：S5-B

**主要变更**：

1. **AIGradingService 完整实现**
   - `backend/app/services/ai_grading_service.py` — 实现触发/查询/确认/拒绝/列表等完整方法

2. **AI 评分业务流程**
   - 候选人提交考试 → AI 自动识别简答题 → 调用 AI 评分 → 保存结果 → HR 查看/确认

3. **AI 评分状态管理**
   - 状态流转：pending → ai_scored → hr_confirmed → completed / rejected
   - 被拒绝后可重新触发（更新原记录）

4. **数据安全保护**
   - 只发送题目/标准答案/评分规则/候选答案
   - 不发送候选人隐私信息

5. **异常处理**
   - AI 调用失败不影响考试提交
   - 记录错误信息，允许后续人工处理

**修改文件**：
- `backend/app/services/ai_grading_service.py` — 完整实现
- `backend/app/models/answer_record.py` — 扩展 AI 评分字段
- `backend/app/models/ai_score_record.py` — AI 评分记录模型
- `backend/app/api/v1/endpoints/ai_grading.py` — AI 阅卷 API
- `ai-service/app/prompts/scoring/v2.yaml` — 增强 Prompt

**测试结果**：21/21 通过

---

# S5-A DeepSeek-V4-Flash 模型接入

**时间**：2026-08-06

**版本**：S5-A

**主要变更**：

1. **AI 配置体系升级**
   - `ai-service/app/core/config.py` — AIConfig 改为 @property 动态读取环境变量
   - 默认模型改为 `deepseek-v4-flash`
   - 默认 Provider 改为 `deepseek`
   - 默认 API Base 改为 `https://api.deepseek.com/v1`

2. **LLMProvider 扩展**
   - `ai-service/app/llm/provider.py` — LLMProvider 枚举新增 DEEPSEEK
   - chat() 方法集成调用日志（请求/响应/错误）
   - 错误分类增强（支持 429 rate limit、unauthorized 等）

3. **新增 AI 健康检查端点**
   - `ai-service/app/api/endpoints/health.py` — 配置检查 + 连接测试
   - `GET /api/health` — 配置状态检查
   - `POST /api/health/connectivity` — 模型连接测试

4. **修复 scoring.py 参数错误**
   - `ai-service/app/api/endpoints/scoring.py` — ModelConfig 参数名 model→name

5. **更新 .env.example**
   - `ai-service/.env.example` — 更新为 DeepSeek-V4-Flash 配置

6. **新增测试**
   - `ai-service/test_deepseek_integration.py` — 24 项测试用例

**影响范围**：
- `ai-service/app/llm/provider.py` — Provider 枚举 + 调用日志
- `ai-service/app/core/config.py` — 配置体系重构
- `ai-service/app/api/endpoints/health.py` — 新增健康检查
- `ai-service/app/api/endpoints/scoring.py` — 参数修复
- `ai-service/app/api/router.py` — 路由注册
- `ai-service/.env.example` — 配置模板更新

**验证结果**：24/24 测试通过

---

# 路由注册异常修复

**时间**：2026-08-06

**版本**：S5.5 修复

**主要变更**：

1. **修复 analysis_report.py import 路径**
   - `from app.core.database import get_db` → `from app.db.session import get_db`

2. **修复 knowledge_base.py import 路径**
   - `from app.api.deps import ...` → `from app.db.session import get_db` + `from app.core.permissions import ...`

3. **修复 exams.py 缺失导入**
   - 补充 `require_authenticated` 到 `from app.core.permissions` 导入

4. **修复 APIRouter 重复 prefix**
   - 移除 `analysis_report.py` 中 `prefix="/analysis-reports"`（已在 router.py 统一配置）
   - 移除 `knowledge_base.py` 中 `prefix="/knowledge-base"`（已在 router.py 统一配置）

**影响范围**：
- `backend/app/api/v1/endpoints/analysis_report.py` — import 路径修复 + prefix 移除
- `backend/app/api/v1/endpoints/knowledge_base.py` — import 路径修复 + prefix 移除
- `backend/app/api/v1/endpoints/exams.py` — 补充 require_authenticated 导入

**验证结果**：
- 105 个路由全部恢复
- 所有业务模块在 OpenAPI 中正常显示
- 回归测试通过

---

# S5.5 招聘辅助分析能力建设

**时间**：2026-08-06

**版本**：S5.5

**主要变更**：

1. **新增候选人分析报告模型**
   - 新增 `backend/app/models/candidate_analysis_report.py` — CandidateAnalysisReport 模型

2. **新增分析 Service**
   - 新增 `backend/app/services/analysis_service.py` — 分析报告生成/查询/审核服务

3. **新增分析 API**
   - 新增 `backend/app/api/v1/endpoints/analysis_report.py` — /api/v1/analysis-reports 端点
   - 支持：生成报告、查询报告、列表查询、HR 审核

4. **新增分析 Prompt**
   - 新增 `ai-service/app/prompts/analysis/v1.yaml` — AI 候选人分析 Prompt v1
   - 严格禁止录用建议，纯辅助分析

5. **新增本地规则分析引擎**
   - 基于 AI 评分结果进行本地规则分析
   - 支持知识掌握度分析、优势分析、薄弱点分析、面试建议生成
   - 不依赖外部 AI 服务

**影响范围**：
- `backend/app/models/` — 新增 candidate_analysis_report.py
- `backend/app/services/` — 新增 analysis_service.py
- `backend/app/api/v1/endpoints/` — 新增 analysis_report.py
- `backend/app/api/v1/router.py` — 注册 analysis_report 路由
- `backend/app/models/__init__.py` — 注册 CandidateAnalysisReport
- `backend/app/schemas/` — 新增 analysis_report.py
- `ai-service/app/prompts/analysis/` — 新增 v1.yaml

---

# S5.4 AI 评分标准知识库建设

**时间**：2026-08-06

**版本**：S5.4

**主要变更**：

1. **新增评分知识库数据模型**
   - 新增 `backend/app/models/position.py` — Position 岗位信息模型
   - 新增 `backend/app/models/scoring_template.py` — ScoringTemplate 评分模板模型
   - 新增 `backend/app/models/scoring_rule.py` — ScoringRule 评分规则模型（带版本控制）
   - 扩展 `backend/app/models/ai_score_record.py` — 新增 scoring_template_id、scoring_rule_versions 字段

2. **新增知识库管理 Service**
   - 新增 `backend/app/services/knowledge_base_service.py` — 知识库 CRUD、版本控制、RAG 检索
   - 支持：岗位管理、评分模板管理、评分规则管理、版本控制、RAG 上下文检索

3. **新增知识库管理 API**
   - 新增 `backend/app/api/v1/endpoints/knowledge_base.py` — /api/v1/knowledge-base 端点
   - 支持：岗位 CRUD、模板 CRUD、规则 CRUD、RAG 检索接口
   - 权限：管理员可创建/修改，HR 可查看

4. **实现 RAG 检索流程**
   - 考试 → 岗位 → 模板 → 规则 自动关联
   - 评分时自动检索知识库规则，注入 AI Prompt 上下文
   - 无知识库时正常降级，不影响评分流程

5. **更新评分 Prompt**
   - 更新 `ai-service/app/prompts/scoring/v2.yaml` — 支持企业评分标准
   - 评分要求增加：优先依据企业标准进行评分

6. **评分版本追溯**
   - AIScoreRecord 记录评分使用的模板 ID 和规则版本
   - 历史评分记录保留原始规则版本关联
   - 评分结果可追溯使用的评分标准

**影响范围**：
- `backend/app/models/` — 新增 position.py、scoring_template.py、scoring_rule.py
- `backend/app/services/` — 新增 knowledge_base_service.py
- `backend/app/api/v1/endpoints/` — 新增 knowledge_base.py
- `backend/app/api/v1/router.py` — 注册 knowledge_base 路由
- `backend/app/models/__init__.py` — 注册新模型
- `backend/app/models/ai_score_record.py` — 新增评分版本字段
- `backend/app/services/ai_grading_service.py` — 集成 RAG 检索
- `ai-service/app/prompts/scoring/v2.yaml` — 支持企业标准

---

# S5.3 AI 智能阅卷 MVP

**时间**：2026-08-06

**版本**：S5.3

**主要变更**：

1. **新增 AI 评分服务**
   - 新增 `backend/app/services/ai_grading_service.py` — AI 阅卷核心 Service
   - 支持：触发 AI 评分、查询评分结果、HR 确认评分、HR 拒绝评分
   - 独立封装 AI 调用逻辑，不侵入考试业务接口

2. **新增 AI 评分记录模型**
   - 新增 `backend/app/models/ai_score_record.py` — AIScoreRecord 模型
   - 独立存储 AI 评分建议，不直接修改 AnswerRecord.score
   - 字段：ai_score, max_score, score_reason, matched_points, missing_points, confidence, review_status
   - 状态流转：pending → ai_scored → hr_confirmed → completed / rejected

3. **新增 AI 阅卷接口**
   - 新增 `backend/app/api/v1/endpoints/ai_grading.py` — AI 阅卷 API 端点
   - 路由前缀：`/api/v1/ai-grading`
   - 接口：trigger（触发AI评分）、results（查询结果）、confirm（HR确认）、reject（HR拒绝）、status（状态查询）、list（列表查询）
   - 权限：仅 HR/Admin 可访问

4. **评分 Prompt v2**
   - 新增 `ai-service/app/prompts/scoring/v2.yaml`
   - 增强：知识点分析（matched_points + missing_points）
   - 结构化输出：score, reason, matched_points, missing_points, confidence

5. **ScoringAgent 增强**
   - 支持动态 Prompt 版本加载
   - 支持 matched_points / missing_points 解析
   - 响应增加 prompt_version、needs_review 元数据

6. **异常处理**
   - AI 服务不可用时降级处理（不影响考试提交）
   - 评分结果异常时标记 needs_review=True
   - 空答案快速处理（直接返回 0 分）

**影响范围**：
- `backend/app/models/` — 新增 ai_score_record.py
- `backend/app/services/` — 新增 ai_grading_service.py
- `backend/app/api/v1/endpoints/` — 新增 ai_grading.py
- `backend/app/api/v1/router.py` — 注册 ai_grading 路由
- `backend/app/models/__init__.py` — 注册 AIScoreRecord
- `ai-service/app/agents/scoring_agent.py` — 增强 Prompt 版本支持
- `ai-service/app/schemas/scoring.py` — 增加 matched_points 字段
- `ai-service/app/prompts/scoring/v2.yaml` — 新增 v2 Prompt
- `backend/app/services/ai_scoring_service.py` — 响应验证增强
- `backend/app/services/grading_service.py` — _save_ai_score 增强

---

# S5.2 AI Tool 调用能力建设

**时间**：2026-08-06

**版本**：S5.2

**主要变更**：
- 增强 BaseTool（标准化返回格式、参数类型校验、参数范围校验）
- 新增 ToolRouter（统一调用入口：权限/参数/执行/审计/异常）
- 新增 ToolAuditService（审计日志查询、工具使用统计、失败分析）
- 新增 GetExamStatisticsTool（考试统计查询工具）
- 更新 exam_tools.py（S5.2 首批 3 个工具注册）
- 新增 test_ai_tools.py（22 用例，全部通过）

**新增文件**：
- `ai-service/app/tools/tool_router.py` — Tool Router 统一路由
- `ai-service/app/tools/tool_audit.py` — Tool 审计服务
- `ai-service/test_ai_tools.py` — S5.2 测试文件

**修改文件**：
- `ai-service/app/tools/base_tool.py` — 增强返回格式和参数校验
- `ai-service/app/tools/exam_tools.py` — 新增工具 + 增强消息格式

**影响范围**：
- AI Service Tool 模块增强，不影响现有评分/报告功能
- 所有新模块独立，不修改 Backend 业务代码

---

# S5.1 AI Agent 基础架构设计

**时间**：2026-08-06

**版本**：S5.1

**主要变更**：
- 新增 Agent 核心模块（会话管理、消息处理）
- 新增 Model Provider 模块（统一 LLM 调用封装）
- 新增 Tool 调用模块（工具基类、注册表、8 个考试工具）
- 新增 Prompt 管理模块（System Prompt 版本化配置）
- 新增 AI Agent API 端点（/agent/chat, /agent/conversations, /agent/tools）
- 新增 AI Agent 测试文件（19 用例，全部通过）

**新增文件**：
- `ai-service/app/agents/conversation.py` — 会话管理
- `ai-service/app/llm/provider.py` — Model Provider
- `ai-service/app/tools/__init__.py` — 工具模块
- `ai-service/app/tools/base_tool.py` — 工具基类
- `ai-service/app/tools/tool_registry.py` — 工具注册表
- `ai-service/app/tools/exam_tools.py` — 考试工具实现
- `ai-service/app/prompts/agent/__init__.py` — Agent Prompt 模块
- `ai-service/app/prompts/agent/system_v1.yaml` — System Prompt
- `ai-service/app/api/endpoints/agent.py` — AI Agent API 端点
- `ai-service/test_ai_agent.py` — 测试文件

**修改文件**：
- `ai-service/app/api/router.py` — 注册 Agent 路由
- `ai-service/main.py` — 注册工具到注册表

**影响范围**：
- AI Service 新增 Agent 能力，不影响现有评分/报告功能
- 所有新模块独立，不修改 Backend 业务代码

---

# S5.0 AI Agent 架构设计能力检查

**时间**：2026-08-06

**版本**：S5.0

**主要变更**：
- 无代码变更（本阶段为架构检查阶段）
- 确认 AI Agent 推荐架构：Tool Calling（优先）+ RAG（后续）
- 确认 AI 能力边界：只读查询 + 信息汇总 + 辅助分析
- 确认 AI 权限方案：用户身份透传 + 权限继承
- 确认风险清单：A 级 3 项、B 级 6 项、C 级 5 项
- 输出《S5.0 AI Agent 架构设计能力检查报告》

**影响范围**：
- 本阶段仅输出架构检查报告，不修改任何业务代码
- 为 S5.1 AI Agent 基础架构设计提供明确方向

---

# S4.4-C1 AI 接入安全基础补充

**时间**：2026-08-06

**版本**：S4.4-C1

**主要变更**：
- 新增 AiCallLog 模型（AI 调用审计日志表）+ Alembic 迁移
- 新增 AiCallLogService（审计日志 Service：创建/更新/查询）
- 新增 DataMaskingMiddleware（数据脱敏中间件：手机号/邮箱/身份证）
- 新增 trace.py（链路追踪模块：trace_id + request_id）
- 新增审计日志查询 API：GET /api/v1/ai-call-logs（管理员）
- 扩展 request_logging.py：支持 trace_id
- 扩展异常处理器：日志含 trace_id
- 新增测试文件 backend/test_ai_security.py（26 用例，全部通过）

**影响范围**：
- `backend/app/models/ai_call_log.py` — 新增
- `backend/app/models/__init__.py` — 修改（注册 AiCallLog）
- `backend/alembic/versions/d4c5e6f7a8b9_add_ai_call_log.py` — 新增
- `backend/app/services/ai_call_log_service.py` — 新增
- `backend/app/core/data_masking.py` — 新增
- `backend/app/core/trace.py` — 新增
- `backend/app/core/request_logging.py` — 修改（支持 trace_id）
- `backend/app/exceptions/handler.py` — 修改（异常含 trace_id）
- `backend/app/api/v1/endpoints/ai_call_logs.py` — 新增
- `backend/app/api/v1/router.py` — 修改（注册审计日志路由）
- `backend/main.py` — 修改（注册脱敏中间件）
- `backend/test_ai_security.py` — 新增

---

# S4.4-C AI Agent 数据访问准备能力检查

**时间**：2026-08-06

**版本**：S4.4-C

**主要变更**：
- 检查 AI 数据访问架构、接口能力、权限控制、数据脱敏、审计能力
- 输出 AI 数据访问边界表（开放/受限/禁止三类数据分类）
- 输出风险清单（B001-B002 中危，C001-C002 低危）
- 检查结论：✅ 通过，可进入 S5 AI Agent 架构设计阶段

**影响范围**：
- 无代码变更（本阶段为检查阶段）
- 文档更新：AI_HANDOVER.md / CHANGE_HISTORY.md / change-log.md

---

# S4.4-B 数据查询接口建设

**时间**：2026-08-06

**版本**：S4.4-B

**主要变更**：
- 扩展 ExamStatisticsService：新增 get_exam_analysis / get_exam_results / get_candidate_exam_history_paginated / get_record_answers 方法
- 扩展考试统计 Schema：新增 ExamAnalysisResponse / ExamResultsResponse / ExamResultItem / CandidateHistoryPaginatedResponse / RecordAnswersResponse / AnswerDetailItem
- 新增考试分析接口 GET /api/v1/exams/{exam_id}/analysis
- 新增考试成绩列表接口 GET /api/v1/exams/{exam_id}/results
- 增强候选人历史接口：支持分页/排序/状态过滤
- 新增答题详情接口 GET /api/v1/exams/{exam_id}/records/{record_id}/answers
- 新增测试文件 backend/test_exam_query.py（27 用例，全部通过）

**影响范围**：
- `backend/app/services/exam_statistics_service.py` — 修改（新增 4 个方法）
- `backend/app/schemas/exam_statistics.py` — 修改（新增 6 个 Schema）
- `backend/app/api/v1/endpoints/exams.py` — 修改（新增 3 个端点）
- `backend/app/api/v1/endpoints/candidates.py` — 修改（增强历史查询）
- `backend/test_exam_query.py` — 新增

---

# S4.4-A 考试基础统计能力建设

**时间**：2026-08-06

**版本**：S4.4-A

**主要变更**：
- 新增统计 Service（ExamStatisticsService）
- 新增考试统计接口 GET /api/v1/exams/{exam_id}/statistics
- 新增候选人历史考试查询接口 GET /api/v1/candidates/{candidate_id}/exam-history
- 新增统计相关 Schema（ExamStatisticsResponse, CandidateHistoryResponse）
- 新增统计测试文件 backend/test_exam_statistics.py（18 用例，全部通过）

**影响范围**：
- `backend/app/services/exam_statistics_service.py` — 新增
- `backend/app/schemas/exam_statistics.py` — 新增
- `backend/app/api/v1/endpoints/candidates.py` — 新增
- `backend/app/api/v1/endpoints/exams.py` — 修改（添加统计端点）
- `backend/app/api/v1/router.py` — 修改（注册 candidates_router）
- `backend/test_exam_statistics.py` — 新增

---

# S4.0 稳定性与 AI 接入前置检查

**时间**：2026-08-05

**版本**：S4.0

**主要变更**：
- 日志体系完善（统一格式 + 请求日志 + 敏感数据过滤）
- 异常处理完善（事务回滚 + 全局异常捕获）
- AI 调用审计日志
- AI Agent 架构规划（AI 服务独立部署）

**影响范围**：
- `backend/app/core/` — 日志与异常配置
- `backend/app/middleware/` — 请求日志中间件
- `backend/app/exceptions/` — 统一异常处理
- `ai-service/` — AI Agent 架构设计

---

# S4.1 考试核心业务能力完善

**时间**：2026-08-05

**版本**：S4.1

**主要变更**：
- 考试状态流转（draft → published → closed）
- 考试发布与关闭接口
- 候选人考试流程完善
- 答案保存与提交逻辑
- 客观题自动评分触发
- AI 评分和报告自动调用

**影响范围**：
- `backend/app/services/exam_service.py` — 考试状态管理
- `backend/app/services/exam_record_service.py` — 答题流程
- `backend/app/services/grading_service.py` — 自动评分
- `backend/app/services/report_service.py` — AI 报告
- `backend/app/api/v1/endpoints/exam_records.py` — 答题接口
- `backend/app/api/v1/endpoints/grading.py` — 评分接口
- `backend/app/api/v1/endpoints/reports.py` — 报告接口

---

# S4.2 固定试卷模板体系

**时间**：2026-08-05

**版本**：S4.2

**主要变更**：
- 新增 `exam_template` 表（试卷模板）
- 新增 `template_question` 表（模板题目）
- `answer_record` 表新增 `question_snapshot` 字段（题目快照）
- 模板 CRUD 接口（增删改查 + 启用/停用）
- 模板题目管理接口（增删改查 + 批量添加 + 导入）
- 基于模板创建考试接口（独立复制题目，数据隔离）
- 前端模板管理页面（列表/创建/编辑/详情）

**影响范围**：
- `backend/app/models/exam_template.py` — 新增模型
- `backend/app/models/template_question.py` — 新增模型
- `backend/app/schemas/template.py` — 新增 Schema
- `backend/app/services/template_service.py` — 新增 Service
- `backend/app/api/v1/endpoints/templates.py` — 新增 API
- `backend/alembic/versions/` — 新增迁移
- `frontend/src/api/template.js` — 新增 API 封装
- `frontend/src/views/admin/template/` — 新增页面（3 个）
- `frontend/src/router/index.js` — 新增路由

---

# S4.3 考试发布与安全体系

## S4.3-A 考试人员管理能力建设

**时间**：2026-08-06

**版本**：S4.3-A

**主要变更**：
- 新增 `exam_participant` 表（考试参与人员）
- 人员 CRUD 接口（单个/批量添加、查询、删除、状态更新）
- 人员状态管理（assigned → not_started → in_progress → submitted → completed）
- 人员状态同步机制（从 exam_record 自动同步）
- 唯一约束：同一考试中手机号不能重复

**影响范围**：
- `backend/app/models/exam_participant.py` — 新增模型
- `backend/app/schemas/participant.py` — 新增 Schema
- `backend/app/services/participant_service.py` — 新增 Service
- `backend/app/api/v1/endpoints/participants.py` — 新增 API
- `backend/alembic/versions/` — 新增迁移
- `frontend/src/api/participant.js` — 新增 API 封装
- `frontend/src/views/admin/exam/ExamParticipants.vue` — 新增组件
- `frontend/src/views/admin/exam/ExamDetail.vue` — 添加人员管理 Tab

---

## S4.3-B 考试安全能力完善

**时间**：2026-08-06

**版本**：S4.3-B

**主要变更**：
- `exam` 表新增 `exam_code` 字段（唯一约束，考试访问凭证）
- `exam_record` 表新增 `exam_code` 字段（凭证快照）
- `exam_record` 表新增 `participant_id` 字段（绑定参与人员，外键）
- 候选人身份验证（exam_code + ExamParticipant 校验）
- 防重复提交机制（未完成允许继续，已完成禁止）
- 提交幂等操作
- 前端凭证输入和验证

**影响范围**：
- `backend/app/models/exam.py` — 新增 exam_code 字段
- `backend/app/models/exam_record.py` — 新增 exam_code、participant_id 字段
- `backend/app/services/exam_record_service.py` — 身份验证 + 防重复逻辑
- `backend/app/api/v1/endpoints/exam_records.py` — 创建接口增加凭证参数
- `backend/app/schemas/exam_record.py` — ExamRecordCreate 新增 exam_code
- `backend/alembic/versions/` — 新增迁移（2 个）
- `frontend/src/views/exam/Entry.vue` — 新增凭证输入和验证
- `frontend/src/stores/exam.js` — createRecord 支持 exam_code 参数

---

## S4.3-C 核心流程测试补充

**时间**：2026-08-06

**版本**：S4.3-C

**主要变更**：
- 新增 `backend/test_core_workflow.py` 测试文件（28 个测试用例）
- 7 大核心流程自动化测试覆盖

**测试覆盖**：
| 测试分类 | 用例数 |
|----------|--------|
| 考试创建流程 | 4 |
| 固定试卷模板流程 | 3 |
| 考试人员管理流程 | 5 |
| 考试访问安全 | 4 |
| 答题流程 | 4 |
| 提交流程 | 4 |
| 权限测试 | 4 |

**影响范围**：
- `backend/test_core_workflow.py` — 新增测试文件

---

# S5.7-A 系统真实业务流程黑盒验收检查

**时间**：2026-08-07

**版本**：S5.7-A

**检查目标**：模拟真实用户操作，从浏览器端验证系统完整业务闭环

**检查范围**：
1. 登录认证流程检查
2. HR考试创建流程检查
3. 试卷/考试资料上传流程检查
4. 考试发布流程检查
5. 候选人考试流程检查
6. 答题提交流程检查
7. AI评分流程检查
8. HR成绩查看流程检查

**检查结果**：❌ 未达到真实使用标准

**通过流程**：
- ✅ 流程1：登录认证流程
- ✅ 流程2：HR考试创建流程
- ✅ 流程4：考试发布流程
- ✅ 流程5：候选人考试流程

**不通过流程**：
- ❌ 流程3：试卷上传（未测试）
- ❌ 流程6：答题提交（数据库问题）
- ❌ 流程7：AI评分（依赖流程6）
- ❌ 流程8：成绩查看（依赖流程6）

**P0 级问题**：
1. 数据库 schema 与 ORM 模型不匹配
   - `answer_record` 表缺少 `ai_status`、`ai_score`、`ai_confidence` 等字段
   - 错误：`OperationalError: no such column: answer_record.ai_status`
   
2. 答题保存接口 500 错误
   - 保存答案时查询不存在的字段导致错误

**P1 级问题**：
1. 考试码未自动生成：创建考试时 `exam_code` 为 null
2. 题目列表查询异常：`/api/v1/questions` 返回 0 题
3. 判断题添加失败：`answer` 字段格式校验问题

**根本原因**：
- 使用 SQLite 数据库但 schema 与 ORM 模型不同步
- SQLite ALTER TABLE 功能受限，无法轻松添加缺失字段

**建议修复方案**：
1. 方案 A：重建 SQLite 数据库（开发环境）
2. 方案 B：切换到 MySQL 生产环境
3. 方案 C：手动迁移 SQLite schema

**下一步计划**：
1. 修复 P0 数据库问题
2. 修复 P1 业务问题
3. 重新执行 S5.7-A 检查

**影响范围**：
- `backend/exam_system.db` — 数据库需重建或迁移
- 所有答题相关接口依赖数据库修复

---

# S5.7-B2 SQLite数据库重建与Schema同步

**时间**：2026-08-07

**版本**：S5.7-B2

**执行目标**：修复 S5.7-A 发现的数据库 Schema 与 ORM 模型不匹配问题

**执行操作**：
1. 备份原数据库：`exam_system_backup_before_rebuild_20260807_092249.db`
2. 删除旧开发数据库：`exam_system.db`
3. 修复 `init_db.py` 导入问题：engine 懒加载导致 ImportError
4. 重新初始化数据库：17 张表全部创建成功

**修复结果**：
- ✅ AnswerRecord 表现在包含全部 22 个字段
- ✅ 缺失的 7 个 AI 评分相关字段已补齐：
  - ai_status, ai_model_used, ai_scored_at, ai_error_message, knowledge_points, matched_points, missing_points
- ✅ 答题保存接口从 500 错误恢复为 200 OK
- ✅ 完整业务流程验证通过：创建考试 → 添加题目 → 发布 → 候选人答题 → 保存答案 → 提交

**修复的代码**：
- `backend/app/db/init_db.py` — 修复 engine 导入方式，添加 models 导入

**影响范围**：
- `backend/exam_system.db` — 已重建
- `backend/app/db/init_db.py` — 已修复

---

# S5.7-C 核心业务链路回归测试

**时间**：2026-08-07

**版本**：S5.7-C

**测试目标**：验证数据库修复后，系统完整招聘考试流程是否恢复

**测试范围**：
1. 用户登录流程测试
2. HR创建考试流程测试
3. 试卷/题目管理流程测试
4. 考试发布流程测试
5. 候选人参加考试流程测试
6. 答题与提交流程测试
7. AI评分链路测试
8. HR成绩查看流程测试
9. 异常测试（重复提交、权限越界）

**测试结果**：❌ 部分通过（通过率 79.3%，23/29 项通过）

**通过流程**：
- ✅ 流程1：用户登录（Admin/HR 登录、Token验证）
- ✅ 流程2：考试创建（创建考试、考试详情查看）
- ✅ 流程3：题目管理（添加单选/判断/简答题、正确端点查询题目）
- ✅ 流程4：考试发布（添加参与人员、发布考试、状态变更）
- ✅ 流程5：候选人考试（创建记录、开始考试、获取试卷）
- ✅ 流程6：答题提交（保存答案、生成AnswerRecord、提交考试）
- ✅ 流程8：成绩查看（成绩列表、答题详情、AI报告）
- ✅ 异常测试：权限越界检查

**不通过流程**：
- ❌ 2.2 考试码生成：`exam_code` 为 null
- ❌ 3.4 题目列表查询：`GET /questions` 返回 405（正确端点为 `GET /exams/{id}/questions`）
- ❌ 7.2-7.4 AI评分链路：AI评分未触发，评分状态为 `not_started`
- ❌ 9.1 重复提交限制：重复提交仍返回 200

**P0 级问题**（核心流程阻塞）：
1. 答案保存不完整：`answer_content` 字段为 null，答案内容未正确保存
2. AI评分未触发：提交考试后未自动触发 AI 评分流程
3. AI评分接口路径问题：`/api/v1/ai-scoring/grade` 返回 404

**P1 级问题**（主要业务异常）：
1. 考试码未自动生成：创建考试时 `exam_code` 为 null
2. 题目列表查询端点不明确
3. 重复提交无限制

**数据库修复验证**：
- ✅ 数据库 Schema 与 ORM 模型一致
- ✅ AnswerRecord 表 AI 字段完整
- ✅ 答题保存接口正常工作（不再出现 500 错误）
- ✅ AnswerRecord 记录正确生成（3条记录）

**AI评分链路验证**：
- ❌ AI评分未自动触发
- ❌ AI评分接口路径待确认
- ❌ 评分结果未保存

**根本原因分析**：
1. 答案保存逻辑中，前端提交的 `answer` 字段可能未正确映射到 `answer_content`
2. 考试提交接口可能未正确触发 AI 评分服务调用
3. AI 评分路由注册可能存在问题

**下一步计划**：
1. 修复答案保存逻辑（answer_content 字段映射问题）
2. 实现 AI 评分自动触发机制
3. 确认并修复 AI 评分接口路径
4. 实现考试码自动生成功能
5. 添加重复提交限制
6. 重新执行 S5.7-C 回归测试

**影响范围**：
- 答案保存服务需检查字段映射
- 考试提交服务需添加 AI 评分触发逻辑
- AI 评分路由需确认并修复

---

# S5.7-D1.5-D DeepSeek真实调用自动化验证

**时间**：2026-08-07

**版本**：S5.7-D1.5-D

**验证目标**：自动验证 DeepSeek 真实调用是否成功

**验证结果**：✅ **通过**

**详细检查**：

1. **环境检查结果** ✅
   - `ai-service/.env`：存在
   - `AI_API_KEY`：已配置（有效）
   - `AI_MODEL_NAME`：deepseek-chat
   - `AI_API_BASE`：https://api.deepseek.com/v1

2. **服务启动结果** ✅
   - ai-service 启动成功
   - `/health` 接口返回正常

3. **API调用结果** ✅
   - `POST /api/scoring/evaluate` 返回 HTTP 200
   - score: 9.0
   - reason: AI 生成的详细评分理由
   - confidence: 0.95

4. **DeepSeek响应结果** ✅
   - Score 非固定值: True
   - Reason 为 AI 生成文本: True
   - Confidence 存在: True
   - 确认：真实调用 DeepSeek API，非 mock 数据

**测试脚本**：`ai-service/run_deepseek_test.py`

**最终结论**：
✅ S5.7-D1.5-D通过

**系统状态**：
- AI 评分链路：✅ 完整可用
- 环境配置加载：✅ 正常
- DeepSeek 真实调用：✅ 成功

---

# S5.7-D1.5-C AI环境配置加载修复

**时间**：2026-08-07

**版本**：S5.7-D1.5-C

**修复目标**：修复 AI 服务环境变量未加载导致 DeepSeek API 调用失败的问题（错误：Illegal header value b'Bearer '）

**根因分析**：
1. `ai-service` 目录下缺失 `.env` 文件（仅有 `.env.example` 模板）
2. `ai-service/app/core/config.py` 未主动调用 `load_dotenv()`，导致即使存在 `.env` 也无法被读取
3. 结果：`os.environ.get("AI_API_KEY", "")` 返回空字符串，构造 `Authorization: Bearer ` 时出错

**修改文件**：
1. `ai-service/app/core/config.py`
   - 增加 `from dotenv import load_dotenv`
   - 在配置读取前执行 `load_dotenv()`

2. `ai-service/requirements.txt`
   - 增加 `python-dotenv==1.0.1`

**验证结果**：
- ✅ 代码修改完成，`config.py` 能够正确加载 `.env` 文件
- ✅ 依赖补充完成，`requirements.txt` 声明了 `python-dotenv`
- ✅ 模拟测试通过：`AI_API_KEY` 能被正确读取

**部署要求**：
- 需将 `ai-service/.env.example` 复制为 `ai-service/.env`
- 需在 `.env` 中填入真实 `AI_API_KEY`
- 重启 `ai-service` 后生效

---

# S5.7-D1 AI评分链路修复

**时间**：2026-08-07

**版本**：S5.7-D1

**修复目标**：恢复 AI 评分完整闭环

**修复内容**：

1. 答案保存修复
   - 文件：`backend/app/schemas/exam_record.py`
   - AnswerCreate Schema 增加 `@model_validator(mode="before")` 自动映射 `answer` → `answer_content`
   - 支持前端两种字段命名（`answer` 和 `answer_content`）

2. AI评分自动触发
   - 文件：`backend/app/api/v1/endpoints/exam_records.py`
   - 新增 `_trigger_auto_grade(record_id)` 后台线程触发函数
   - submit_exam 端点在提交成功后自动触发 AI 评分
   - AI 评分在后台线程执行，不阻塞主请求
   - 评分失败不影响考试提交结果

3. AI评分接口路径整理
   - 确认所有 AI 相关接口路径
   - 后端接口：`/api/v1/ai-scoring/evaluate`、`/api/v1/ai-grading/*`
   - AI服务：`http://localhost:8001/api/scoring/evaluate`

4. 评分结果保存增强
   - 文件：`backend/app/services/grading_service.py`
   - `_save_ai_score` 增加 `ai_status`、`ai_scored_at`、`matched_points`、`missing_points` 字段保存

**测试结果**：
- ✅ 答案保存验证：3道题的 answer_content 均非空
- ✅ AI评分触发验证：提交后自动完成评分（status: completed）
- ✅ 评分结果保存：AI评分状态、分数、理由、置信度均正确保存
- ⚠️ AI实际评分需配置 AI_API_KEY（当前未配置）

**AI评分链路**：
```
候选人提交答案 → 保存完整答案 → 提交考试 → 后台触发自动评分
→ 客观题自动评分 → 主观题AI评分 → 保存评分结果 → 更新考试状态
```

**修改文件**：
- `backend/app/schemas/exam_record.py`：AnswerCreate 字段兼容
- `backend/app/api/v1/endpoints/exam_records.py`：AI 评分触发
- `backend/app/services/grading_service.py`：评分结果保存增强

**影响范围**：
- 前端：无修改，兼容现有字段命名
- 后端：3个文件修改
- AI服务：无修改
- 数据库：无修改

---

# S5.7-D1.5 DeepSeek真实调用验证

**时间**：2026-08-07

**版本**：S5.7-D1.5

**验证目标**：确认系统是否能够真实调用DeepSeek模型完成评分

**验证结果**：❌ AI调用未通过（AI_API_KEY 未配置）

**详细发现**：

1. **环境配置状态**
   - 问题：`AI_API_KEY` 未在任何环境配置中设置
   - AI-Service 目录下没有 `.env` 文件
   - 只有 `.env.example` 模板
   - 后端 `.env` 也未包含 `AI_SERVICE_URL` 等 AI 相关配置

2. **AI模型配置状态（正确）**
   - Model Name: `deepseek-v4-flash` ✅
   - API Base: `https://api.deepseek.com/v1` ✅
   - Provider: `deepseek` ✅
   - 模型名称与实际 API 规范一致

3. **AI调用错误分析**
   - 错误：`Illegal header value b'Bearer '`
   - 原因：API Key 为空，httpx 拒绝 `Bearer ` 格式的非法请求头
   - 系统正确捕获并记录错误，未产生虚假评分数据

4. **异常处理验证（通过）**
   - ✅ 考试提交成功（状态: submitted），不受AI失败影响
   - ✅ 评分失败被记录在 `ai_reason` 字段
   - ✅ 评分流程正确完成（status: completed）
   - ✅ AI调用日志完整记录

5. **数据库保存验证（通过）**
   - ✅ AnswerRecord.answer_content: 正确保存
   - ✅ AnswerRecord.ai_reason: 保存了完整错误信息
   - ✅ AnswerRecord.ai_status: 正确标记
   - ✅ GradingRecord: 评分流程完整记录

**系统稳定性**：
- AI评分链路：✅ 完整可用
- 异常处理：✅ 完善
- 真实AI调用：❌ 需配置 API Key

**后续步骤**：
1. 在 `ai-service/` 目录创建 `.env` 文件
2. 设置 `AI_API_KEY=sk-xxx`（从 DeepSeek 控制台获取）
3. 重启 AI-Service
4. 重新执行真实AI调用验证
