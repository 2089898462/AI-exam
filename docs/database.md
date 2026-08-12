# 数据库设计

## 技术选型
- 数据库：MySQL 8.0
- 存储引擎：InnoDB（支持事务、外键）
- 默认字符集：utf8mb4
- ORM：SQLAlchemy 2.0
- 迁移工具：Alembic

## 实体关系（ER）

```
┌──────────┐       ┌──────────┐       ┌────────────┐
│   user   │1──N──>│   exam   │1──N──>│  question  │
└──────────┘       └──────────┘       └────────────┘
      │                  │                  │
      │                  │                  │
      │                 1│                 1│
      │                  │                  │
      │                  ▼                  ▼
      │            ┌──────────────┐  ┌────────────────┐
      │            │ exam_record  │1──N──>│ answer_record  │
      │            └──────────────┘  └────────────────┘
      │                 │1
      │                 │
      │                 ▼
      │          ┌──────────────┐
      │          │  ai_report   │
      │          └──────────────┘
      │
      └── (candidate embedded in exam_record, no FK)
```

### 关系说明

| 关系 | 类型 | 说明 |
|------|------|------|
| user → exam | 1:N | 一个HR可以创建多场考试 |
| exam → question | 1:N | 一场考试包含多道题目 |
| exam → exam_record | 1:N | 一场考试可以被多位候选人参加 |
| exam_record → answer_record | 1:N | 一次考试记录对应多道题目的答案 |
| question → answer_record | 1:N | 一道题目可以被多人回答 |
| exam_record → ai_report | 1:1 | 一次考试记录生成一份AI报告 |

> **设计说明**：候选人不是系统用户，采用嵌入式身份信息（candidate_name/candidate_phone/candidate_email）存储在 exam_record 中，无需 candidate_user 表。

## 核心表设计

---

### 1. user（用户表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 用户ID |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| password_hash | VARCHAR(256) | NOT NULL | 密码哈希值（bcrypt） |
| display_name | VARCHAR(64) | NOT NULL | 显示名称 |
| email | VARCHAR(128) | UNIQUE, NULLABLE | 邮箱 |
| phone | VARCHAR(20) | NULLABLE | 手机号 |
| role | ENUM('admin','hr','candidate') | NOT NULL, DEFAULT 'candidate' | 角色：管理员/HR/候选人 |
| status | ENUM('active','disabled','pending') | NOT NULL, DEFAULT 'active' | 账号状态 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否启用（兼容字段） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `ix_user_username`: UNIQUE (username)
- `ix_user_email`: UNIQUE (email)

---

### 2. exam（考试表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 考试ID |
| title | VARCHAR(200) | NOT NULL | 考试名称 |
| description | TEXT | NULLABLE | 考试说明 |
| duration_minutes | INT | NOT NULL | 考试时长（分钟） |
| pass_score | DECIMAL(5,2) | NOT NULL, DEFAULT 0 | 及格分数 |
| status | ENUM('draft','published','closed') | NOT NULL, DEFAULT 'draft' | 状态：草稿/已发布/已关闭 |
| created_by | BIGINT | FK → user.id, NOT NULL | 创建人 |
| published_at | DATETIME | NULLABLE | 发布时间 |
| closed_at | DATETIME | NULLABLE | 关闭时间 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_exam_created_by`: (created_by)
- `idx_exam_status`: (status)
- `idx_exam_created_at`: (created_at)

---

### 3. question（题目表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 题目ID |
| exam_id | BIGINT | FK → exam.id, NOT NULL | 所属考试 |
| type | ENUM('single_choice','multiple_choice','true_false','short_answer') | NOT NULL | 题目类型 |
| content | TEXT | NOT NULL | 题目内容 |
| options | JSON | NULLABLE | 选项（选择题使用） |
| answer | TEXT | NOT NULL | 标准答案 |
| score | DECIMAL(5,2) | NOT NULL, DEFAULT 0 | 分值 |
| sort_order | INT | NOT NULL, DEFAULT 0 | 排序序号 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**options 格式（JSON）：**
```json
// 单选题 / 多选题
[
  {"label": "A", "content": "选项内容"},
  {"label": "B", "content": "选项内容"},
  {"label": "C", "content": "选项内容"},
  {"label": "D", "content": "选项内容"}
]

// 判断题 / 简答题：options 为 null
```

**answer 格式：**
| 题目类型 | answer 示例 | 说明 |
|----------|-------------|------|
| single_choice | `"A"` | 正确选项标签 |
| multiple_choice | `"A,B,C"` | 逗号分隔的正确选项 |
| true_false | `"true"` 或 `"false"` | 正确判断 |
| short_answer | `"标准答案文本"` | 标准答案 |

**索引：**
- `idx_question_exam_id`: (exam_id)
- `idx_question_sort`: (exam_id, sort_order)

---

### 4. exam_record（考试记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录ID |
| exam_id | BIGINT | FK → exam.id, NOT NULL, INDEX | 考试ID |
| candidate_name | VARCHAR(64) | NOT NULL | 候选人姓名（嵌入式身份） |
| candidate_phone | VARCHAR(20) | NULLABLE | 候选人手机 |
| candidate_email | VARCHAR(128) | NULLABLE | 候选人邮箱 |
| status | ENUM('not_started','in_progress','submitted','graded') | NOT NULL, DEFAULT 'not_started' | 状态 |
| started_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 开始时间 |
| submitted_at | DATETIME | NULLABLE | 提交时间 |
| score | DECIMAL(8,2) | NULLABLE | 总分（评分后写入） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**状态枚举说明：**
| 值 | 说明 |
|----|------|
| not_started | 已创建未开始 |
| in_progress | 考试进行中 |
| submitted | 已提交待评分 |
| graded | 已评分 |

**索引：**
- `ix_exam_record_exam_id`: (exam_id)

---

### 5. answer_record（答题记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录ID |
| exam_record_id | BIGINT | FK → exam_record.id, NOT NULL, INDEX | 考试记录ID |
| question_id | BIGINT | FK → question.id, NOT NULL, INDEX | 题目ID |
| answer_content | TEXT | NULLABLE | 候选人答案内容 |
| score | DECIMAL(5,2) | NULLABLE | 得分（评分后写入） |
| is_correct | BOOLEAN | NULLABLE | 客观题自动判分标记 |
| ai_comment | TEXT | NULLABLE | AI 评分评论文本 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `ix_answer_record_exam_record_id`: (exam_record_id)
- `ix_answer_record_question_id`: (question_id)
- `uq_answer_record_question`: UNIQUE (exam_record_id, question_id) — 一道题在一个考试记录中只能有一条答案

---

### 6. ai_report（AI报告表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 报告ID |
| exam_record_id | BIGINT | FK → exam_record.id, UNIQUE, NOT NULL | 考试记录ID |
| strengths | JSON | NOT NULL | 优势能力 |
| weaknesses | JSON | NOT NULL | 薄弱能力 |
| learning_suggestions | JSON | NOT NULL | 学习建议 |
| raw_report | TEXT | NULLABLE | AI原始返回（调试用） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**strengths / weaknesses / learning_suggestions 格式（JSON）：**
```json
["能力描述1", "能力描述2"]
```

**索引：**
- `idx_report_exam_record_id`: UNIQUE (exam_record_id)

---

### 7. grading_record（评分记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 评分记录ID |
| exam_record_id | BIGINT | FK → exam_record.id, UNIQUE, NOT NULL | 考试记录ID（一对一） |
| status | ENUM('pending','grading','completed','failed') | NOT NULL, DEFAULT 'pending' | 评分状态 |
| grading_type | ENUM('auto','ai','hybrid') | NOT NULL, DEFAULT 'auto' | 评分类型：自动/AI/混合 |
| total_score | DECIMAL(8,2) | NULLABLE | 最终总分 |
| auto_score | DECIMAL(8,2) | NULLABLE | 客观题得分 |
| ai_score | DECIMAL(8,2) | NULLABLE | AI评分得分 |
| passed | BOOLEAN | NULLABLE | 是否及格 |
| started_at | DATETIME | NULLABLE | 评分开始时间 |
| completed_at | DATETIME | NULLABLE | 评分完成时间 |
| error_message | TEXT | NULLABLE | 错误信息（评分失败时记录） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**状态枚举说明：**
| 值 | 说明 |
|----|------|
| pending | 待评分 |
| grading | 评分中 |
| completed | 评分完成 |
| failed | 评分失败 |

**评分类型说明：**
| 值 | 说明 |
|----|------|
| auto | 自动评分（仅客观题） |
| ai | AI评分（仅主观题） |
| hybrid | 混合评分（客观题+AI评分） |

**索引：**
- `uq_grading_record_exam_record`: UNIQUE (exam_record_id) — 一个考试记录只能有一条评分记录

---

### 8. question_score_rule（题目评分规则表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 规则ID |
| exam_id | BIGINT | FK → exam.id, NOT NULL, INDEX | 考试ID |
| question_type | ENUM('single_choice','multiple_choice','true_false','short_answer') | NOT NULL | 题型 |
| score_method | ENUM('auto_compare','ai_score','manual') | NOT NULL, DEFAULT 'auto_compare' | 评分方法 |
| pass_score | DECIMAL(5,2) | NOT NULL, DEFAULT 0 | 该题型及格分 |
| weight | DECIMAL(3,2) | NOT NULL, DEFAULT 1.00 | 权重 |
| is_enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否启用 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**评分方法说明：**
| 值 | 说明 |
|----|------|
| auto_compare | 自动比对标准答案（适用客观题） |
| ai_score | AI评分（适用主观题） |
| manual | 手动评分（HR人工批改） |

**业务规则：**
- 同一考试同一题型只能有一条规则（Service层保证唯一性）
- 默认规则：单选/多选/判断 → auto_compare，简答 → ai_score

**索引：**
- `ix_question_score_rule_exam_id`: (exam_id)

---

## MVP 需求覆盖检查

| 需求 | 覆盖表 | 实现方式 |
|------|--------|----------|
| HR创建考试 | exam, question | exam 记录考试信息，question 记录题目 |
| 导入考试JSON | exam, question | JSON 解析后写入 exam + question 表 |
| 发布/关闭考试 | exam | 修改 exam.status 字段 |
| 查看考试列表 | exam | 按 status/created_at 查询 |
| 候选人进入考试 | exam_record | 创建 exam_record 记录，嵌入 candidate_name/candidate_phone/candidate_email |
| 候选人答题 | answer_record | 逐题写入 answer_record.answer_content |
| 提交答案 | exam_record | 更新 exam_record.status + submitted_at |
| 客观题自动评分 | answer_record | 系统比对标准答案后写入 score + is_correct |
| 主观题AI评分 | answer_record | AI 服务评分后写入 score + ai_comment |
| AI能力分析报告 | ai_report | 根据考试结果生成并存至 ai_report |
| 查看成绩 | exam_record + answer_record | 聚合查询 score 和各题得分 |

## 命名规范

- 表名：小写 + 下划线，如 `exam_record`
- 主键：统一 `id BIGINT AUTO_INCREMENT`
- 外键：`{目标表名}_id`，如 `exam_id`
- 时间字段：`created_at`, `updated_at`
- 枚举字段：下划线命名，如 `in_progress`
- 索引前缀：`idx_`，唯一索引加 `UNIQUE`