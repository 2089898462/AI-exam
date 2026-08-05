# 考试 JSON 导入格式规范

> 版本：v1.0
> 适用系统：企业 AI 智能考试与能力评估系统
> 说明：HR 通过标准 JSON 文件批量导入考试题目，系统负责解析、校验并存储。

---

## 1. 整体结构

一份完整的考试 JSON 文件包含 **考试信息** 和 **题目列表** 两部分。

```json
{
  "title": "2026 年度安全生产培训考试",
  "description": "新员工入职安全培训考核",
  "duration_minutes": 60,
  "pass_score": 60,
  "exam_code": "EXAM-2026-001",
  "questions": [
    { ... },
    { ... }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 考试名称，1-200 字符 |
| description | string | ❌ | 考试说明，建议不超过 500 字符 |
| duration_minutes | integer | ✅ | 考试时长（分钟），范围 1-1440 |
| pass_score | number | ❌ | 及格分数，默认 0 |
| exam_code | string | ❌ | 考试编号，建议唯一，不超过 50 字符 |
| questions | array | ✅ | 题目列表，至少 1 道题 |

---

## 2. 题目结构

每道题目包含以下字段：

```json
{
  "type": "single_choice",
  "content": "以下哪项是安全生产的第一责任人？",
  "question_no": "Q1",
  "category": "基础安全",
  "options": [
    { "label": "A", "text": "企业主要负责人" },
    { "label": "B", "text": "安全管理人员" },
    { "label": "C", "text": "班组长" },
    { "label": "D", "text": "普通员工" }
  ],
  "answer": "A",
  "score": 10,
  "sort_order": 1
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | ✅ | 题型，可选值见下文 |
| content | string | ✅ | 题目内容，1-5000 字符 |
| question_no | string | ❌ | 题目编号，便于识别，不超过 20 字符 |
| category | string | ❌ | 题目分类，便于筛选，不超过 50 字符 |
| options | array | 视题型而定 | 选项列表，仅选择题需要 |
| answer | string | ✅ | 标准答案，格式见下文 |
| score | number | ❌ | 分值，默认 0 |
| sort_order | integer | ❌ | 排序序号，默认 0，按升序排列 |

---

## 3. 支持题型

### 3.1 单选题（single_choice）

**说明**：从多个选项中选择唯一正确答案。

```json
{
  "type": "single_choice",
  "content": "以下哪项是安全生产的第一责任人？",
  "options": [
    { "label": "A", "text": "企业主要负责人" },
    { "label": "B", "text": "安全管理人员" },
    { "label": "C", "text": "班组长" },
    { "label": "D", "text": "普通员工" }
  ],
  "answer": "A",
  "score": 10
}
```

**校验规则**：
- `options` 至少 2 个选项
- 每个 option 必须包含 `label` 和 `text`
- `answer` 必须是某个 option 的 `label`

### 3.2 多选题（multiple_choice）

**说明**：从多个选项中选择两个或以上正确答案。

```json
{
  "type": "multiple_choice",
  "content": "以下属于个人防护用品的有哪些？",
  "options": [
    { "label": "A", "text": "安全帽" },
    { "label": "B", "text": "安全带" },
    { "label": "C", "text": "计算器" },
    { "label": "D", "text": "护目镜" }
  ],
  "answer": "A,B,D",
  "score": 15
}
```

**校验规则**：
- `options` 至少 2 个选项
- 每个 option 必须包含 `label` 和 `text`
- `answer` 为多个 label 用英文逗号分隔，如 `"A,B,D"`
- answer 中的 label 必须都存在于 options 中

### 3.3 问答题（essay）

**说明**：开放式问答，由 AI 服务进行评分。

```json
{
  "type": "essay",
  "content": "请简述企业安全生产责任制的主要内容。",
  "answer": "企业安全生产责任制的主要内容包括：1. 企业主要负责人对安全生产全面负责；2. 各部门负责人对本部门安全生产负责；3. 岗位员工对本岗位安全生产负责……",
  "score": 20
}
```

**校验规则**：
- `options` 可为空或省略
- `answer` 为参考答案文本，不能为空
- 答案用于 AI 评分时的对比参考

---

## 4. 完整示例

以下是一个包含三种题型的完整考试 JSON 文件：

```json
{
  "title": "2026 年度安全生产培训考试",
  "description": "新员工入职安全培训考核，涵盖基础安全知识和应急处置流程",
  "duration_minutes": 60,
  "pass_score": 60,
  "exam_code": "EXAM-2026-001",
  "questions": [
    {
      "type": "single_choice",
      "content": "安全生产法规定，生产经营单位的主要负责人对本单位安全生产工作负什么责任？",
      "question_no": "Q1",
      "category": "法律法规",
      "options": [
        { "label": "A", "text": "直接责任" },
        { "label": "B", "text": "全面责任" },
        { "label": "C", "text": "领导责任" },
        { "label": "D", "text": "间接责任" }
      ],
      "answer": "B",
      "score": 10,
      "sort_order": 1
    },
    {
      "type": "multiple_choice",
      "content": "以下属于特种作业的是哪些？",
      "question_no": "Q2",
      "category": "作业管理",
      "options": [
        { "label": "A", "text": "电工作业" },
        { "label": "B", "text": "焊接与热切割作业" },
        { "label": "C", "text": "办公室文员工作" },
        { "label": "D", "text": "高处作业" }
      ],
      "answer": "A,B,D",
      "score": 15,
      "sort_order": 2
    },
    {
      "type": "essay",
      "content": "请结合岗位实际，谈谈如何在日常工作中落实安全生产责任制。",
      "question_no": "Q3",
      "category": "综合应用",
      "answer": "参考答案：1. 认真学习安全生产法律法规和公司规章制度；2. 严格遵守操作规程，不违章作业；3. 主动排查安全隐患并及时上报；4. 积极参加安全培训和应急演练；5. 发现他人违章行为及时制止。",
      "score": 20,
      "sort_order": 3
    }
  ]
}
```

---

## 5. 常见错误

| 错误 | 原因 | 修正方式 |
|------|------|----------|
| `questions` 字段缺失 | 未提供题目列表 | 至少包含 1 道题目 |
| `type` 值无效 | 使用了不支持的题型 | 使用 single_choice / multiple_choice / essay |
| 单选题缺少 options | 选择题必须提供选项 | 至少 2 个选项 |
| answer 的 label 不在 options 中 | 答案引用了不存在的选项 | 确保 answer 值与某个 option 的 label 一致 |
| 多选答案格式错误 | 使用中文逗号或空格分隔 | 使用英文逗号，如 `"A,B,D"` |
| JSON 语法错误 | 格式不合法（多余逗号、引号缺失等） | 使用 JSON 校验工具检查 |

---

## 6. 导入接口

- **方法**：`POST`
- **路径**：`/api/v1/exams/{exam_id}/import`
- **Content-Type**：`multipart/form-data`
- **参数**：
  - `file`：JSON 文件（.json）
- **成功响应**：
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "imported_count": 3,
      "exam_id": 1
    }
  }
  ```
- **失败响应**：
  ```json
  {
    "code": 400,
    "message": "题目校验失败",
    "data": {
      "errors": [
        "第 1 题: 单选题至少需要 2 个选项",
        "第 2 题: 答案 'E' 不在选项列表中"
      ]
    }
  }
  ```

---

## 7. 注意事项

1. **UTF-8 编码**：JSON 文件必须使用 UTF-8 编码
2. **文件大小**：建议不超过 5MB
3. **导入范围**：一次性导入的题目数量建议不超过 500 道
4. **事务一致性**：导入过程中若某道题校验失败，全部回滚
5. **草稿状态**：仅允许对草稿状态的考试进行导入
6. **考试信息**：JSON 中的 title/description/duration_minutes 等字段会覆盖考试的当前值