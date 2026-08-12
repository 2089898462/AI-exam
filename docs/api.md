# API 接口设计

## 基础信息
- Base URL: `/api/v1`
- 数据格式: JSON
- 时间格式: ISO 8601
- 认证方式: JWT Bearer Token（候选人端点除外）

---

## 1. 认证接口（Auth）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/auth/register` | ❌ 无需 | 用户注册 |
| POST | `/auth/login` | ❌ 无需 | 用户登录，返回 JWT |
| GET | `/auth/me` | ✅ 需要 | 获取当前用户信息 |
| POST | `/auth/logout` | ✅ 需要 | 退出登录 |

---

## 2. 考试管理（Exams）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/exams` | ✅ HR/Admin | 创建考试 |
| GET | `/exams` | ✅ HR/Admin | 考试列表（支持筛选、分页） |
| GET | `/exams/{id}` | ✅ HR/Admin | 考试详情（含题目列表） |
| PUT | `/exams/{id}` | ✅ HR/Admin | 更新考试 |
| DELETE | `/exams/{id}` | ✅ HR/Admin | 删除考试 |
| POST | `/exams/{id}/publish` | ✅ HR/Admin | 发布考试 |
| POST | `/exams/{id}/close` | ✅ HR/Admin | 关闭考试 |
| GET | `/exams/{id}/questions` | ✅ HR/Admin | 获取考试题目列表 |
| POST | `/exams/{id}/import` | ✅ HR/Admin | 导入 JSON 试卷（multipart/form-data） |
| GET | `/exams/{id}/info` | ❌ 无需 | 获取公开考试信息（候选人入口） |

---

## 3. 题目管理（Questions）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/questions` | ✅ HR/Admin | 创建题目 |
| DELETE | `/questions/{id}` | ✅ HR/Admin | 删除题目 |

---

## 4. 候选人考试记录（Exam Records）

### 候选人端点（无需认证）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/exam-records` | ❌ 无需 | 创建候选人考试记录 |
| GET | `/exam-records/{id}` | ❌ 无需 | 获取考试记录详情 |
| GET | `/exam-records/{id}/paper` | ❌ 无需 | 获取考试试卷（安全过滤，不含答案） |
| POST | `/exam-records/{id}/start` | ❌ 无需 | 开始考试（状态：not_started → in_progress） |
| POST | `/exam-records/{id}/answers` | ❌ 无需 | 保存单题答案 |
| POST | `/exam-records/{id}/answers/batch` | ❌ 无需 | 批量保存答案 |
| GET | `/exam-records/{id}/answers` | ❌ 无需 | 获取历史答案（刷新恢复） |
| POST | `/exam-records/{id}/submit` | ❌ 无需 | 提交考试（状态：in_progress → submitted） |
| GET | `/exam-records/{id}/grading` | ❌ 无需 | 获取评分状态（候选人查看评分进度） |

### HR 管理端点（需认证）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/exams/{exam_id}/records` | ✅ HR/Admin | 查看某考试的候选人记录列表 |

---

## 5. 评分管理（Grading）

### 评分流程端点（HR/Admin）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/exams/records/{id}/grading` | ✅ HR/Admin | 创建评分记录 |
| GET | `/exams/records/{id}/grading` | ✅ HR/Admin | 获取评分记录详情 |
| POST | `/exams/records/{id}/grading/start` | ✅ HR/Admin | 开始评分（pending → grading） |
| POST | `/exams/records/{id}/grading/complete` | ✅ HR/Admin | 完成评分 |
| POST | `/exams/records/{id}/auto-grade` | ✅ HR/Admin | 执行自动评分（客观题 + AI 主观题） |

### 评分规则端点（HR/Admin）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/exams/{exam_id}/score-rules` | ✅ HR/Admin | 创建评分规则 |
| GET | `/exams/{exam_id}/score-rules` | ✅ HR/Admin | 获取评分规则列表 |
| PUT | `/exams/score-rules/{rule_id}` | ✅ HR/Admin | 更新评分规则 |
| DELETE | `/exams/score-rules/{rule_id}` | ✅ HR/Admin | 删除评分规则 |
| POST | `/exams/{exam_id}/score-rules/init` | ✅ HR/Admin | 初始化默认评分规则 |

### 评分结果查询（HR/Admin）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/grading/results` | ✅ HR/Admin | 评分结果列表（支持分页、筛选） |
| GET | `/grading/results/{exam_record_id}` | ✅ HR/Admin | 评分结果详情（含答题对比） |

---

## 6. AI 评分接口（AI Scoring）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/ai-scoring/evaluate` | ✅ HR/Admin | 触发 AI 评分（单题） |
| GET | `/ai-scoring/health` | ✅ HR/Admin | AI 服务健康检查 |

### AI-Service 内部接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `ai-service:8001/api/v1/scoring/evaluate` | AI-Service 评分接口 |
| POST | `ai-service:8001/api/v1/report/generate` | AI-Service 报告生成接口 |

---

## 7. AI 报告管理（Reports）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/reports/generate` | ✅ HR/Admin | 生成 AI 报告（触发报告生成流程） |
| GET | `/reports/exam-records/{exam_record_id}` | ✅ HR/Admin | 按考试记录查询报告 |
| GET | `/reports/{report_id}` | ✅ HR/Admin | 获取报告详情 |
| GET | `/reports` | ✅ HR/Admin | 报告列表（支持分页、状态筛选） |
| DELETE | `/reports/{report_id}` | ✅ HR/Admin | 删除报告 |

---

## 8. 健康检查

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health` | ❌ 无需 | 基础健康检查 |
| GET | `/health/db` | ❌ 无需 | 数据库连接检查 |

---

## 请求/响应示例

### 创建考试记录（候选人进入考试）

**请求**：
```json
POST /api/v1/exam-records
{
  "exam_id": 1,
  "candidate_name": "张三",
  "candidate_phone": "13800138000",
  "candidate_email": "zhangsan@example.com"
}
```

**响应**：
```json
{
  "code": 201,
  "message": "created",
  "data": {
    "id": 1,
    "exam_id": 1,
    "candidate_name": "张三",
    "status": "not_started",
    "started_at": "2026-08-05T10:00:00"
  }
}
```

### 获取考试试卷

**请求**：
```json
GET /api/v1/exam-records/1/paper
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "exam_id": 1,
    "exam_title": "前端工程师招聘考试",
    "duration_minutes": 60,
    "pass_score": 60,
    "question_count": 3,
    "questions": [
      {
        "id": 1,
        "type": "single_choice",
        "content": "Vue3 使用什么构建工具？",
        "options": [
          {"label": "A", "content": "Webpack"},
          {"label": "B", "content": "Vite"},
          {"label": "C", "content": "Rollup"}
        ],
        "score": 10
      }
    ],
    "record_id": 1,
    "candidate_name": "张三",
    "status": "not_started"
  }
}
```

---

## 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 业务异常（BusinessException） |
| 401 | 未认证 / Token 无效（UnauthorizedException） |
| 403 | 权限不足（ForbiddenException） |
| 404 | 资源不存在（NotFoundException） |
| 422 | 参数校验失败（ValidationException） |
| 500 | 服务器内部错误 |

## 状态码响应格式

```json
{
  "code": 422,
  "message": "参数校验失败",
  "data": {
    "errors": ["exam_id: Field required"]
  }
}
```

---

## 版本历史

| 日期 | 版本 | 修改内容 |
|------|------|----------|
| 2026-08-05 | 3.0 | 新增评分管理、AI 评分、AI 报告接口，补全缺失的候选人端点 |
| 2026-08-05 | 2.0 | 更新为实际已实现接口，补充请求/响应示例 |
| - | 1.0 | 初始版本（待定） |
