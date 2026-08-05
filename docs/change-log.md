# 变更记录

## 2026-08-04

### S0 - 项目初始化
- 创建项目目录结构
- 创建后端骨架（FastAPI + SQLAlchemy）
- 创建前端骨架（Vue3 + Vite + Element Plus）
- 创建 AI 服务骨架

### 架构优化
- 重构 Backend 目录：增加 db/, exceptions/
- 重构 AI-Service 目录：增加 agents/, llm/, evaluation/
- 优化 Prompt 管理：YAML 版本化
- 优化 Frontend 目录：增加 api/, layouts/, hooks/
- 优化 Docker 配置：dev/prod 分离
- 建立完整文档体系

### S1.2 - 数据库模型与迁移
- 完善数据库基础层：db/base.py, db/session.py, db/init_db.py
- 创建 6 个 ORM 模型：user, exam, question, exam_record, answer_record, ai_report
- 配置 Alembic 迁移环境（env.py, alembic.ini, script.py.mako）
- 生成第一次迁移：init_mvp_tables（db2a7edfcf67）
- 通过 SQLite 验证迁移成功（6 表全部创建，结构正确）
- 更新 sql/init.sql 为 MySQL DDL 参考脚本

### S1.3 - 后端基础 API 架构建设
- 创建 API 路由架构：api/v1/router.py（统一注册中心，/api/v1 前缀）
- 创建健康检查端点：health.py（基础检查 + 数据库连接检查）
- 实现统一响应格式：utils/response.py（success/error/created/paginated）
- 创建 Pydantic Schema 层：schemas/（common, user, exam, question, record）
- 创建 Service 业务层：services/（base CRUD + user/exam/question/record 服务）
- 实现统一异常体系：exceptions/（AppException + 5 种业务异常 + 全局处理器）
- 更新 main.py 入口：集成异常处理器、CORS 中间件、路由挂载
- 验证：应用正常启动，API 健康检查接口返回正确

### S1.3 架构修复 - 高优先级问题
- **P0-1 密码安全**：创建 utils/password.py，使用 bcrypt 哈希替代明文存储；user_service.py 新增 hash_password/verify_password/authenticate 方法
- **P0-2 数据库初始化统一**：废弃 sql/init.sql 作为初始化入口，保留为 DDL 参考文档；统一使用 Alembic
- **P1-3 JSON 类型通用化**：修改模型文件（question.py, answer_record.py, ai_report.py）和 Alembic 迁移文件，从 mysql.JSON() 改为通用 sa.JSON()
- **P1-4 配置外置**：health 接口版本号从硬编码改为读取 settings.VERSION
- **P1-5 AI-Service 基础结构**：创建 api/router.py、agents/base_agent.py、完善 llm/client.py（LLMClient 封装）、更新 main.py 集成路由

### AI 上下文交接文档
- 创建 docs/AI_HANDOVER.md
- 包含 11 个章节：项目基本信息、技术架构、已确认决策、开发阶段、数据库状态、后端状态、AI 模块状态、前端状态、已知问题、后续路线、AI 开发规则
- 包含 AI 接手说明：必读文件清单、接手确认事项

### S2.1 - 考试资源管理后端基础接口
- **数据库调整**：exam 表新增 `exam_code`、`published_at`；question 表新增 `question_no`、`category`
- **Alembic 迁移**：新增 `a1b2c3d4e5f6_add_exam_code_and_q_fields.py`，升级到 head
- **Schema 层**：完善 exam.py（ExamCreate/ExamUpdate/ExamResponse/ExamListResponse/ExamDetailResponse/ExamPublishResponse/ExamCloseResponse）、question.py（QuestionCreate/QuestionUpdate/QuestionResponse/QuestionResponseWithoutAnswer）
- **Service 层**：实现 exam_service.py（创建/修改/删除/发布/关闭/列表/详情/题目计数）、question_service.py（CRUD + 题型校验 + 批量创建 + 清空）
- **API 层**：exams.py（考试 CRUD + 发布/关闭 + 题目列表）、questions.py（题目 CRUD）
- **修复**：exam 详情序列化（改用 QuestionResponse.model_validate 替代 __dict__）
- **验证**：15 项测试全部通过，覆盖创建/查询/更新/删除/发布/关闭/权限校验/状态机

### S2.2 - 固定试卷 JSON 导入模块
- **JSON 格式规范**：创建 docs/exam-json-format.md，定义三种题型（single_choice/multiple_choice/essay）的标准 JSON 结构、字段含义、校验规则、常见错误
- **导入 Schema**：创建 schemas/exam_import.py（OptionImportSchema/QuestionImportSchema/ExamImportSchema/ImportResult），实现题型/选项/答案的深度校验
- **导入 Service**：创建 services/exam_import_service.py，支持 JSON 解析 → 数据校验 → 考试信息覆盖 → 题目批量入库，事务一致性保证（失败自动回滚）
- **API 端点**：新增 `POST /api/v1/exams/{exam_id}/import`，接受 multipart/form-data 文件上传
- **类型映射**：JSON 的 `essay` 类型自动映射到数据库 `short_answer`，无需新增枚举
- **异常增强**：ValidationException/NotFoundException/BusinessException 支持 data 参数，返回详细错误信息
- **依赖新增**：requirements.txt 添加 python-multipart==0.0.9
- **数据库变化**：无（复用 S2.1 迁移，无新增字段/表）
- **测试结果**：11 项测试全部通过
  - 成功导入 3 道题（单选+多选+问答）✅
  - 考试详情查询（含题目列表）✅
  - 题目列表查询✅
  - 考试标题/描述/时长被 JSON 覆盖✅
  - 无效 JSON 校验拦截（3 种错误同时检出）✅
  - 事务回滚（校验失败后题目数量不变）✅
  - 非 JSON 文件拦截✅
  - 已发布考试禁止导入✅
  - 不存在的考试返回 404✅
  - 空题目数组校验✅

### S2.3.1 - HR 后台前端基础框架
- **Router 配置**：完善 router/index.js，添加 /admin、/admin/exams、/admin/exams/create、/admin/exams/:id/edit、/admin/exams/:id 路由，支持懒加载
- **Layout 开发**：完善 AdminLayout.vue，实现 Header（面包屑、用户下拉）、Sidebar（Logo + 菜单）、RouterView
- **菜单实现**：考试管理菜单（考试列表、创建考试），支持路由跳转与高亮
- **API 层**：完善 request.js（axios 拦截器：错误处理、401 跳转、超时提示），创建 api/exam.js（examApi + questionApi 封装），页面禁止直接调用 axios
- **页面创建**：
  - ExamList.vue：考试列表页（搜索/筛选/分页/状态标签/岗位列/操作按钮：查看/编辑/发布/关闭/删除）
  - ExamCreate.vue：创建/编辑考试页（表单校验 + 岗位字段 + 题目列表展示 + JSON 导入入口）
  - ExamDetail.vue：考试详情页（只读信息 + 岗位字段 + 题目列表 + 关闭操作）
- **依赖新增**：@element-plus/icons-vue
- **状态标签修复**：统一 statusTagType 返回 'info' 作为默认值，消除 Vue 警告
- **测试结果**：
  - 首页自动跳转到 /admin/exams ✅
  - 侧边栏菜单正确渲染并高亮当前页 ✅
  - 面包屑导航正确显示 ✅
  - 考试列表页正常加载数据 ✅
  - 创建考试页表单完整渲染 ✅
  - 考试详情页信息正确展示 ✅
  - 控制台无错误 ✅

### S2.3.2 - HR 考试管理功能完善
- **API 封装升级**：api/exam.js 增加规范化方法（getExamList/getExamDetail/createExam/updateExam/deleteExam/publishExam/closeExam），保留旧方法别名以兼容，页面禁止直接调用 axios
- **ExamList.vue 完善**：
  - 新增"岗位"列显示 position 字段
  - 操作列扩展为 260 宽度，包含查看/编辑/发布/关闭/删除按钮（按状态条件显示）
  - 所有接口调用改为新命名方法（getExamList/publishExam/deleteExam/closeExam）
  - 编辑入口改为路由 `/admin/exams/:id/edit`
- **ExamCreate.vue 完善**：
  - 新增"岗位"字段（position，maxlength 100）
  - 保存成功后创建流程跳回列表（/admin/exams），编辑流程跳回详情
  - 加载数据使用 getExamDetail，保存使用 createExam/updateExam
- **ExamDetail.vue 完善**：
  - 新增"岗位"字段展示
  - 使用 getExamDetail 加载，closeExam 关闭
- **路由调整**：新增 `/admin/exams/:id/edit` 独立路由（复用 ExamCreate.vue），解决编辑入口无法加载表单的问题
- **测试结果（浏览器端到端验证）**：
  - 考试列表加载 ✅
  - 创建考试（名称/编码/岗位/说明/时长）✅
  - 查看详情（含岗位、状态、题目数量）✅
  - 编辑考试（加载原数据、修改岗位、保存）✅
  - 发布考试（发布后操作列变化）✅
  - 关闭考试 ✅
  - 删除考试 ✅

### S2.3.3 - JSON 导入 + 题目管理页面
- **新增组件**：
  - `src/components/exam/ImportExamDialog.vue`：JSON 文件上传对话框，支持拖拽/点击上传、格式校验（仅 .json）、成功/失败结果展示（考试名称、导入数量、错误详情列表）
  - `src/components/exam/QuestionTable.vue`：题目列表展示组件，字段：题号、题型、分类、内容、分数、排序、操作（删除），支持只读模式
- **新增 API**：
  - `src/api/question.js`：getQuestions / createQuestion / deleteQuestion（含 listByExam/create/delete 旧方法兼容别名）
  - `examApi.importExam(id, file)`：使用 FormData + multipart/form-data 调用 `POST /api/v1/exams/{id}/import`
- **页面改造** `ExamDetail.vue`：
  - 新增"导入试卷"按钮（仅草稿状态可用）
  - 集成 ImportExamDialog，导入成功后自动刷新详情
  - 集成 QuestionTable，展示题目列表并支持删除题目
  - 导入成功后刷新考试详情、删除后同步刷新
- **示例文件**：新增 `frontend/public/sample-exam.json`（4 道题样例）和 `frontend/public/invalid.json`（错误格式用例）
- **测试结果**：
  - 创建考试 → 详情页加载 ✅
  - JSON 导入成功（imported_count=4、exam_title 正确）✅
  - 题目列表展示（8 列完整：#、题号、题型、分类、内容、分数、排序、操作）✅
  - 删除题目（后端接口 200 返回 success，前端列表刷新）✅
  - 错误 JSON 导入（422 + 错误详情列表：title/duration_minutes/questions Field required）✅
  - 浏览器控制台无错误 ✅

### S2.4.1 - 后端用户认证基础
- **密码安全**：
  - 新增 `app/core/security.py`（hash_password / verify_password / create_access_token / verify_token / get_current_user_id）
  - 基于 bcrypt 的哈希校验；JWT 使用 HS256 + 可配置 SECRET_KEY 与过期时间
  - `app/utils/password.py` 改为对 security 层的兼容封装
  - 注册新用户时强制写入 bcrypt 哈希，禁止明文存储
- **数据库迁移**：新增 `alembic/versions/c1d2e3f4a5b6_add_user_status.py`
  - user 表新增 `status` 字段（active / disabled / pending，默认 active）
  - 扩展 user.role 枚举支持 `hr` 角色（admin / candidate / hr）
- **Service 层**：新增 `app/services/auth_service.py`
  - register（用户名/邮箱重复校验 + 哈希入库）
  - login（bcrypt 校验 + 账号启用状态校验 + JWT 签发）
  - get_current_user（Token → DB 查询 → 激活状态校验）
- **API 层**：
  - `app/api/v1/deps/auth.py`：Bearer Token 解析、当前用户依赖、角色校验依赖
  - `app/api/v1/endpoints/auth.py`：`POST /api/v1/auth/login`、`POST /api/v1/auth/register`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout`
  - 在 `v1_router` 中以 `/auth` 前缀挂载
- **Schema**：新增 `app/schemas/auth.py`（LoginRequest / RegisterRequest / TokenResponse / CurrentUserResponse）
- **依赖**：requirements.txt 新增 `pyjwt==2.9.0`
- **测试结果（httpx 端到端）**：
  - 注册返回 201，自动登录返回 JWT ✅
  - `/auth/me` 使用 Token 成功返回当前用户（role=hr、status=active）✅
  - 错误密码登录返回 401「用户名或密码错误」✅
  - 无 Token 访问 `/auth/me` 返回 401「缺少 Authorization 头」✅
  - 数据库 `password_hash` 以 `$2b$12$` 开头，确认为 bcrypt 哈希（明文禁止）✅

### S2.4.2 - Backend API 权限保护
- **依赖模块**：新增 `app/core/dependencies.py`
  - `_extract_token`：统一 Bearer Token 解析
  - `get_current_user`：鉴权依赖（必须登录，查库校验激活状态）
  - `get_current_user_id_from_header`：轻量依赖（仅解析 ID，不查库）
  - `get_optional_current_user`：可选鉴权（无 Token 返回 None）
- **权限模块**：新增 `app/core/permissions.py`
  - `require_roles([...])`：角色校验工厂
  - `require_admin`：仅 admin 角色
  - `require_hr_or_admin`：HR 或 admin 角色（HR 后台主要使用）
  - `require_authenticated`：仅需登录
- **JWT 配置集中化**：
  - `app/core/config.py` 新增 JWT_SECRET_KEY / JWT_ALGORITHM / JWT_ACCESS_TOKEN_EXPIRE_MINUTES
  - `app/core/security.py` 改为从 `settings` 读取配置，严禁硬编码
- **Service 层改造**：
  - `ExamService`：方法签名改为接收 `current_user: User`；`_ensure_owner_or_admin` 允许 admin 绕过所有权检查；`list_exams` admin 可查看全部，普通用户仅查看自己
  - `QuestionService`：同样改为接收 `current_user`，admin 绕过所有权
  - `ExamImportService`：改为 `current_user` 参数，admin 绕过所有权
- **API 端点保护**（统一使用 `Depends(require_hr_or_admin)`）：
  - `exams.py`：全部 8 个端点（CRUD + 发布/关闭/列表题目/导入）已鉴权
  - `questions.py`：全部 2 个端点（创建/删除）已鉴权
  - 所有 `MOCK_USER_ID` 已替换为 `current_user.id` / `current_user`
- **测试结果（httpx 端到端 15 项）**：
  - 无 Token → 401 ✅
  - 错误 Token（`invalid-token`）→ 401 ✅
  - 候选角色 Token → 403（"需要 HR 或管理员权限"）✅
  - HR Token → 200/201 正常访问 ✅
  - 认证接口 `/auth/login` / `/auth/register` 仍可匿名访问 ✅
  - `/auth/me` 未携带 Token 返回 401 ✅
  - Admin 绕过所有权，HR 只能操作自己的数据 ✅

### S2.4.3 - 前端登录系统开发
- **Token 管理**：新增 `src/utils/auth.js`，使用 localStorage 存储 JWT Token（setToken/getToken/removeToken）
- **Auth API 封装**：新增 `src/api/auth.js`，封装 login/getCurrentUser 接口，页面禁止直接调用 axios
- **Pinia 用户 Store**：新增 `src/stores/user.js`，实现 login/logout/getUserInfo 及 isLoggedIn/username/displayName/role getter
- **登录页面**：新增 `src/views/login/Login.vue`，表单校验 + 用户名密码登录 + 登录成功跳转 /admin/exams
- **Axios 拦截器升级**：修改 `src/api/request.js`
  - 请求拦截：自动附加 Authorization: Bearer {token} 头
  - 响应拦截：401 状态码清除 token 并跳转 /login
- **路由守卫**：新增 `src/router/guard.js`
  - 无 token 访问 /admin* → 跳转 /login
  - 已有 token 访问 /login → 跳转 /admin/exams
- **路由配置更新**：`src/router/index.js` 添加 /login 路由，集成路由守卫
- **AdminLayout 集成**：用户下拉显示当前用户名，退出登录确认后清除 token 并跳转
- **测试结果（浏览器端到端验证）**：
  - 无 token 访问 /admin/exams → 自动跳转 /login ✅
  - 登录页表单元素完整显示 ✅
  - 错误凭据登录 → 后端返回 422 错误 ✅
  - 正确凭据登录 → token 保存 + 跳转 /admin/exams ✅
  - 刷新页面 → 登录状态保持 ✅
  - 清除 token 后访问受保护页面 → 自动跳转 /login ✅
  - 退出登录 → 确认对话框 + 清除 token + 跳转 /login ✅

### S2.5 - Release Fix 阶段
- **数据库修复**：
  - `exam_record.py`：新增 `updated_at` 字段（DateTime, onupdate=func.now()）
  - `ai_report.py`：新增 `updated_at` 字段（DateTime, onupdate=func.now()）
  - 新增 Alembic migration `d4e5f6g7h8i9_add_updated_at_to_records.py`
  - 执行 `alembic upgrade head` 迁移成功
- **文件上传安全修复**：
  - `exams.py`：新增 `MAX_FILE_SIZE = 5 * 1024 * 1024`（5MB）
  - `import_exam` 接口增加双重检查：
    1. 检查 `file.size`（如果可用）是否超过限制
    2. 使用 `file.read(MAX_FILE_SIZE + 1)` 限制读取大小，防止超大文件一次性加载到内存
  - 超限返回明确错误："文件大小超过限制，最大支持 5MB"
- **测试结果**：
  - 小文件（353 bytes）导入成功 ✅
  - 大文件（>5MB）被正确拒绝，返回 422 + 明确错误信息 ✅
  - 数据库 exam_record/ai_report 表均有 updated_at 字段 ✅

### S3.1.1 - 候选人考试流程数据库扩展
- **设计理念**：候选人不是系统用户，采用考试记录嵌入式身份信息（candidate_name/candidate_phone/candidate_email），不创建 candidate_user 表
- **exam_record 表重构**：
  - 移除 `user_id` 外键（候选人非系统用户）
  - 新增 `candidate_name` VARCHAR(64) NOT NULL（候选人姓名）
  - 新增 `candidate_phone` VARCHAR(20) NULL（候选人手机）
  - 新增 `candidate_email` VARCHAR(128) NULL（候选人邮箱）
  - 重命名 `total_score` → `score` NUMERIC(8,2)
  - 扩展状态枚举：`not_started` / `in_progress` / `submitted` / `graded`（新增 not_started）
  - 保留：exam_id, status, started_at, submitted_at, created_at, updated_at
- **answer_record 表重构**：
  - 重命名 `answer` → `answer_content` TEXT
  - 移除 `score_type` ENUM（auto/ai）
  - 重命名 `score_detail` → `ai_comment` TEXT（JSON→Text，存储 AI 评分文本评论）
  - 新增 `is_correct` BOOLEAN NULL（客观题自动判分标记）
  - 保留：exam_record_id, question_id, score, created_at, updated_at
- **user 模型调整**：
  - 移除 `exam_records = relationship("ExamRecord", back_populates="user")`（因 exam_record 不再关联 user）
- **Schema 层更新**（schemas/record.py）：
  - `ExamRecordCreate`：新增 candidate_name/candidate_phone/candidate_email 参数
  - `ExamRecordResponse`：新增候选人字段、score 替代 total_score
  - `AnswerResponse`：answer→answer_content, 移除 score_type, score_detail→ai_comment, 新增 is_correct
  - 新增 `ExamRecordListResponse` 列表响应 Schema
- **Service 层更新**（services/record_service.py）：
  - `start_exam(exam_id, candidate_name, candidate_phone, candidate_email)`：嵌入式候选人信息创建
  - `submit_exam(record_id)`：移除 user_id 权限校验，改为状态机校验
  - `save_answer(record_id, question_id, answer_content)`：使用 answer_content 字段
  - 新增 `get_by_exam(exam_id)`：获取某考试的所有记录
  - 新增 `get_detail_with_answers(record_id)`：获取记录详情含答题
- **Alembic 迁移**：新增 `e1f2a3b4c5d6_s311_restructure_record_tables.py`
  - 使用 CREATE TABLE + 数据迁移 + 替换的安全策略
  - upgrade：exam_record 和 answer_record 全字段重构
  - downgrade：完整回滚到 S2 表结构
- **数据关系**：exam(1:N)→exam_record(1:N)→answer_record(1:N)←question
- **测试结果**（S2 全量回归 + S3 Service 测试）：
  - Health/Register/Login ✅
  - Create/List/Detail/Publish Exam ✅
  - Create/Get Question ✅
  - JSON Import ✅
  - Auth Me ✅
  - start_exam(候选人张三) → candidate_name/candidate_phone 正确写入 ✅
  - save_answer → answer_content 正确写入 ✅
  - submit_exam → status=submitted, submitted_at 自动填充 ✅
  - get_by_exam / get_detail_with_answers ✅

### S3.1.2 - Service 层开发
- **设计理念**：拆分 ExamRecordService 和 AnswerRecordService，职责单一，便于独立测试和扩展
- **新增 exam_record_service.py**：
  - `create_exam_record(exam_id, candidate_name, candidate_phone, candidate_email)`：创建考试记录，校验考试存在 + 候选人姓名非空，初始状态 not_started
  - `get_record_by_id(record_id)`：查询考试记录，不存在抛 NotFoundException
  - `start_exam(record_id)`：状态流转 not_started → in_progress，记录 started_at
  - `submit_exam(record_id)`：状态流转 in_progress → submitted，记录 submitted_at
  - `list_exam_records(exam_id, status=None)`：按考试ID查询记录列表，支持状态过滤
  - `get_detail_with_answers(record_id)`：获取记录详情含答题和考试信息
- **新增 answer_record_service.py**：
  - `save_answer(record_id, question_id, answer_content)`：保存单题答案，校验考试存在/题目存在/题目归属/状态允许答题，支持幂等更新
  - `save_answers_batch(record_id, answers)`：批量保存答案，保证事务一致性（失败 rollback）
  - `get_answers_by_record(record_id)`：查询某考试记录的所有答题
- **RecordService 重构**：
  - 原 RecordService 改为兼容层，内部委托 ExamRecordService + AnswerRecordService
  - 保持原有 API 签名不变，向后兼容
- **业务校验规则**：
  - 答题状态允许：not_started / in_progress（提交后不可修改）
  - 题目归属校验：必须属于当前考试
  - 唯一性约束：同一考试记录同一题目只能有一条答案（幂等更新）
- **异常使用**：全部使用统一异常模块（NotFoundException / BusinessException / ValidationException），无 HTTPException
- **单元测试**：28 个测试用例全通过
  - TestCreateExamRecord（3）：成功 / 考试不存在 / 姓名为空
  - TestGetRecordById（2）：成功 / 不存在
  - TestStartExam（2）：成功 / 状态错误
  - TestSubmitExam（3）：成功 / 未开始 / 已提交
  - TestListExamRecords（3）：按考试 / 空列表 / 按状态过滤
  - TestGetDetailWithAnswers（1）：成功
  - TestSaveAnswer（6）：新答案 / 幂等更新 / 记录不存在 / 题目不存在 / 题目归属错误 / 提交后保存
  - TestSaveAnswersBatch（5）：成功 / 空列表 / 缺 question_id / 部分更新 / 提交后保存
  - TestGetAnswersByRecord（3）：成功 / 空列表 / 记录不存在
  - 6 表结构验证：字段/索引/外键全部正确 ✅

### S3.1.3 - API 接口开发
- **新增 Schema** `schemas/exam_record.py`：
  - `ExamRecordCreate`：创建考试记录请求（exam_id + candidate_name + 可选 phone/email）
  - `ExamRecordResponse`：考试记录基本信息响应
  - `ExamRecordDetailResponse`：考试记录详情响应（含答题列表）
  - `ExamRecordListResponse`：考试记录列表响应（HR 查看）
  - `AnswerCreate`：单题答题请求
  - `AnswerBatchCreate`：批量答题请求（answers 列表）
  - `AnswerResponse`：答题记录响应
  - 所有 Schema 继承 BaseSchema（from_attributes=True），支持 ORM 对象校验
- **新增 API 端点** `api/v1/endpoints/exam_records.py`：
  - 候选人端点（无需认证）：
    - `POST /api/v1/exam-records`：创建候选人考试记录（create_exam_record）
    - `GET /api/v1/exam-records/{id}`：获取考试记录详情
    - `POST /api/v1/exam-records/{id}/start`：开始考试（not_started → in_progress）
    - `POST /api/v1/exam-records/{id}/answers`：保存单题答案
    - `POST /api/v1/exam-records/{id}/answers/batch`：批量保存答案
    - `POST /api/v1/exam-records/{id}/submit`：提交考试（in_progress → submitted）
  - HR 管理端点（需 JWT + HR/Admin 权限）：
    - `GET /api/v1/exams/{exam_id}/records`：查看某考试的候选人考试记录列表（支持 status 筛选）
- **路由注册** `api/v1/router.py`：
  - `exam_record_router`：候选人端点，prefix `/exam-records`，tag「候选人考试记录」
  - `exam_record_hr_router`：HR 管理端点，prefix `/exams`，tag「考试记录管理」
- **异常处理**：统一使用 AppException 体系，handler.py 全局异常处理器自动映射 HTTP 状态码
  - NotFoundException → 404（考试不存在、记录不存在、题目不存在）
  - BusinessException → 400（状态流转错误、重复提交、已提交后答题）
  - ValidationException → 422（参数校验失败、题目归属错误）
  - ForbiddenException → 403（非 HR/Admin 访问）
  - UnauthorizedException → 401（无 Token 访问 HR 端点）
- **权限控制**：
  - 候选人端点：无需认证（候选人非系统用户，嵌入式身份信息）
  - HR 端点：使用 `require_hr_or_admin` 依赖，校验用户角色
- **测试**：20 个 API 测试用例全通过
  - TestCreateExamRecord（4）：创建成功 / 最小参数 / 考试不存在 / 空姓名
  - TestGetExamRecord（2）：查询成功 / 不存在
  - TestStartExam（2）：开始成功 / 重复开始
  - TestSaveAnswer（4）：保存成功 / 幂等更新 / 提交后保存被拒 / 错误题目
  - TestSaveAnswersBatch（2）：批量成功 / 空列表校验
  - TestSubmitExam（2）：提交成功 / 未开始提交被拒
  - TestHRListExamRecords（4）：HR 列表成功 / 未授权 401 / 错误角色 403 / 状态筛选
  - Service 层 28 个测试全通过（无回归）
- **修复项**：
  - 测试 SQLite 使用 StaticPool 共享内存连接，解决跨连接表不可见问题
  - Schema 继承 BaseSchema，支持 from_attributes ORM 对象校验

### S3.2.1 - 候选人考试入口页面
- **新增前端页面** `views/exam/Entry.vue`：
  - 考试信息展示（标题、描述、时长、题量、及格分）
  - 候选人身份表单（姓名必填、手机/邮箱选填 + 格式校验）
  - 考试记录创建流程（表单校验 → API 调用 → 成功状态展示）
  - 成功面板（绿色对勾 + 记录详情 + 跳转答题页按钮）
- **新增 API 封装** `api/examRecord.js`：
  - `getExamInfo(examId)`：获取公开考试信息（无需认证）
  - `createRecord(data)`：创建考试记录
  - `getRecord(id)`：获取考试记录
  - `startExam(id)`：开始考试
  - `submitExam(id)`：提交考试
  - `saveAnswer(recordId, data)`：保存单题答案
  - `saveAnswersBatch(recordId, data)`：批量保存答案
  - `listRecords(examId)`：HR 查看考试记录列表
- **新增 Pinia Store** `stores/exam.js`：
  - 状态：examId / recordId / candidateName / candidatePhone / candidateEmail / status
  - Getters：hasRecord / isStarted
  - Actions：setExamInfo / clearRecord / createRecord / startExam / submitExam
- **新增公开后端端点** `GET /api/v1/exams/{exam_id}/info`：
  - 无需认证，返回考试基本信息（标题、描述、时长、及格分、题量、状态）
  - 候选人入口页面专用
- **路由注册** `router/index.js`：
  - `/exam/:id` → ExamEntry（候选人入口页，无需登录）
- **浏览器测试**：全流程验证通过
  - 页面加载 → 表单填写 → 创建记录 → 成功面板展示 → 无控制台错误
  - 考试信息正确加载（标题、描述、时长、题量、及格分）
  - API 请求 POST /api/v1/exam-records 返回 201 Created
  - 候选人页面无需登录即可访问（不受 /admin 路由守卫限制）

### S3.2.2 - 候选人答题页面基础开发
- **新增后端公开端点** `GET /api/v1/exam-records/{record_id}/paper`：
  - 返回考试试卷（考试信息 + 题目列表 + 候选人信息）
  - 无需认证，候选人答题页面专用
  - 题目不含正确答案（安全考虑）
  - 新增 Schema：PaperQuestionResponse / ExamPaperResponse
- **扩展前端 API** `api/examRecord.js`：
  - 新增 `getExamPaper(recordId)` 方法
- **扩展 Pinia Store** `stores/exam.js`：
  - 新增状态：examInfo / questions / answers
  - 新增 getters：answeredCount / totalQuestions
  - 新增 actions：loadExamPaper / setAnswer / _initAnswers
  - 答案初始化：多选题为 []，其他题为 ''
- **新增答题组件** `components/exam/`：
  - `QuestionCard.vue`：题目卡片容器，根据题型动态渲染
  - `ChoiceQuestion.vue`：选择题组件（单选/多选/判断题），支持选项格式兼容解析
  - `TextQuestion.vue`：简答题组件（textarea）
- **新增答题页面** `views/exam/Exam.vue`：
  - 顶部：考试名称 + 元信息 + 候选人信息
  - 左侧答题卡导航网格（5列布局，已答/当前/未答状态）
  - 右侧题目卡片（上一题/下一题导航）
  - 完成按钮带未答题确认弹窗
  - 答案切换不丢失（Pinia Store 持久化）
- **路由注册** `router/index.js`：
  - `/exam/record/:id` → ExamTaking（答题页，无需登录）
- **修改入口页** `Entry.vue`：
  - 跳转路径从 `/exam/${examId}/exam` 改为 `/exam/record/${recordId}`
- **浏览器测试**：全流程验证通过
  - 入口页 → 创建记录 → 成功面板 → 答题页
  - 三种题型正常渲染：单选题（single_choice）、多选题（multiple_choice）、简答题（short_answer）
  - 答案切换不丢失（状态持久化验证通过）
  - 答题卡导航可点击切换题目
  - 完成按钮弹出未答题确认对话框
  - 无控制台错误