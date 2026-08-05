# API 接口设计

## 基础信息
- Base URL: `/api/v1`
- 数据格式: JSON
- 时间格式: ISO 8601

## 接口列表（待定）

### 考试管理
- `POST /exams` - 创建考试
- `GET /exams` - 考试列表
- `GET /exams/{id}` - 考试详情
- `PUT /exams/{id}` - 更新考试
- `POST /exams/{id}/publish` - 发布考试
- `POST /exams/import` - 导入JSON

### 考试参与
- `GET /exams/{id}/enter` - 进入考试
- `POST /exams/{id}/submit` - 提交答案

### 结果查询
- `GET /exams/{id}/results` - 考试成绩
- `GET /exams/{id}/results/{user_id}` - 用户成绩详情
- `GET /exams/{id}/results/{user_id}/report` - AI报告

## 错误码
- 200: 成功
- 400: 业务异常
- 404: 资源不存在
- 500: 服务器错误