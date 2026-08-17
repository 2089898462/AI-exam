<template>
  <div class="grading-result-detail">
    <el-page-header @back="goBack" content="返回列表" style="margin-bottom: 16px" />

    <template v-if="loading">
      <el-card v-loading="true">
        <div style="height: 300px"></div>
      </el-card>
    </template>

    <template v-else-if="detail">
      <!-- 基本信息卡片 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span class="card-title">候选人信息</span>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="候选人">{{ detail.candidate_name }}</el-descriptions-item>
              <el-descriptions-item label="手机">{{ detail.candidate_phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="邮箱" :span="2">{{ detail.candidate_email || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span class="card-title">考试信息</span>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="考试">{{ detail.exam_title }}</el-descriptions-item>
              <el-descriptions-item label="考试ID">{{ detail.exam_id }}</el-descriptions-item>
              <el-descriptions-item label="考试记录ID" :span="2">{{ detail.exam_record_id }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <!-- 评分结果展示 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-card class="score-card">
            <el-statistic
              title="AI评分"
              :value="detail.total_score || 0"
              :precision="1"
            />
            <div class="score-detail">
              <span class="score-sub">客观题: {{ detail.auto_score || 0 }}</span>
              <span class="score-sub">AI简答题: {{ detail.ai_score || 0 }}</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="score-card">
            <template v-if="detail.review_score !== null && detail.review_score !== undefined">
              <el-statistic
                title="HR复核分数"
                :value="detail.review_score"
                :precision="1"
              />
              <div class="score-status">
                <el-tag type="warning" size="small">HR已复核</el-tag>
              </div>
            </template>
            <template v-else>
              <el-statistic title="HR复核分数" value="—" />
              <div class="score-status">
                <el-tag type="info" size="small">暂无复核</el-tag>
              </div>
            </template>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="score-card final-score">
            <el-statistic
              title="最终成绩"
              :value="finalScore"
              :precision="1"
              :class="{ 'pass': finalPassed, 'fail': finalPassed === false }"
            />
            <div class="score-status">
              <el-tag v-if="finalPassed !== null && finalPassed !== undefined" :type="finalPassed ? 'success' : 'danger'" size="small">
                {{ finalPassed ? '及格' : '不及格' }}
              </el-tag>
              <el-tag v-if="detail.review_score !== null && detail.review_score !== undefined" type="warning" size="small" style="margin-left: 4px">
                取HR复核
              </el-tag>
              <el-tag v-else type="info" size="small" style="margin-left: 4px">
                取AI评分
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <template #header>
              <span class="card-title">HR复核操作</span>
            </template>
            <el-form :model="reviewForm" label-width="90px" size="small">
              <el-form-item label="复核分数">
                <el-input-number
                  v-model="reviewForm.review_score"
                  :min="0"
                  :max="maxScore"
                  :precision="1"
                  :step="0.5"
                  placeholder="输入复核分数"
                  controls-position="right"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="复核备注">
                <el-input
                  v-model="reviewForm.review_comment"
                  type="textarea"
                  :rows="2"
                  placeholder="修改原因"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="small" :loading="submitting" @click="submitReview">保存复核</el-button>
                <el-button size="small" @click="resetReviewForm">重置</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <!-- AI评分详情（折叠展示） -->
      <el-card style="margin-bottom: 16px">
        <template #header>
          <div class="card-header-with-toggle">
            <span class="card-title">AI评分详情</span>
            <el-tag size="small" type="info">客观题: {{ detail.auto_score || 0 }} | AI简答题: {{ detail.ai_score || 0 }}</el-tag>
          </div>
        </template>
        <el-collapse v-model="activeCollapse">
          <el-collapse-item title="客观题得分详情" name="auto">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="客观题总分">{{ detail.auto_score || 0 }}</el-descriptions-item>
              <el-descriptions-item label="总题数">{{ detail.statistics.total_questions }}</el-descriptions-item>
              <el-descriptions-item label="已答题数">{{ detail.statistics.answered_count }}</el-descriptions-item>
              <el-descriptions-item label="正确题数">{{ detail.statistics.correct_count }}</el-descriptions-item>
            </el-descriptions>
          </el-collapse-item>
          <el-collapse-item title="AI简答题评分详情" name="ai">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="AI评分总分">{{ detail.ai_score || 0 }}</el-descriptions-item>
              <el-descriptions-item label="AI置信度">{{ aiConfidenceText }}</el-descriptions-item>
            </el-descriptions>
            <el-divider content-position="left">AI评分详情</el-divider>
            <el-table :data="aiScoredAnswers" border stripe size="small" v-if="aiScoredAnswers.length > 0">
              <el-table-column prop="question_no" label="题号" width="80" />
              <el-table-column prop="question_content" label="题目" min-width="200" show-overflow-tooltip />
              <el-table-column prop="ai_score" label="AI得分" width="100">
                <template #default="{ row }">
                  <span class="text-success">{{ row.ai_score ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="score" label="最终得分" width="100">
                <template #default="{ row }">
                  <span>{{ row.score ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="ai_confidence" label="置信度" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.ai_confidence !== null && row.ai_confidence !== undefined" :type="row.ai_confidence >= 0.8 ? 'success' : row.ai_confidence >= 0.6 ? 'warning' : 'danger'" size="small">
                    {{ (row.ai_confidence * 100).toFixed(0) }}%
                  </el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="ai_reason" label="评分原因" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <span>{{ row.ai_reason || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无AI评分详情" :image-size="80" />
          </el-collapse-item>
        </el-collapse>
      </el-card>

      <!-- 评分状态和时间 -->
      <el-card style="margin-bottom: 16px">
        <template #header>
          <span class="card-title">评分状态</span>
        </template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="评分状态">
            <el-tag :type="statusTagType(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="评分类型">
            <el-tag :type="gradingTypeTag(detail.grading_type)">{{ gradingTypeText(detail.grading_type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ detail.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ detail.complete_time || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.error_message" label="错误信息" :span="4">
            <span style="color: #f56c6c">{{ detail.error_message }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 统计信息 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="总题数" :value="detail.statistics.total_questions" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="已答题数" :value="detail.statistics.answered_count" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="正确题数" :value="detail.statistics.correct_count" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="正确率" :value="detail.statistics.correct_rate" :precision="1" suffix="%" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 答题详情 -->
      <el-card>
        <template #header>
          <span class="card-title">答题详情</span>
        </template>
        <el-table :data="detail.answers" border stripe>
          <el-table-column prop="question_no" label="题号" width="80" />
          <el-table-column prop="question_type" label="题型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ questionTypeText(row.question_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="question_content" label="题目" min-width="200" show-overflow-tooltip />
          <el-table-column label="选项/答案" min-width="200">
            <template #default="{ row }">
              <div v-if="row.options" class="options-list">
                <div v-for="(opt, idx) in row.options" :key="idx" class="option-item">
                  <span class="option-label">{{ String.fromCharCode(65 + idx) }}.</span>
                  <span>{{ typeof opt === 'string' ? opt : (opt.content || opt.label || '') }}</span>
                </div>
              </div>
              <div v-else class="text-content">{{ row.question_content }}</div>
            </template>
          </el-table-column>
          <el-table-column label="候选人答案" width="150">
            <template #default="{ row }">
              <span :class="{ 'correct': row.is_correct, 'wrong': row.is_correct === false }">
                {{ row.candidate_answer || '未作答' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="标准答案" width="120">
            <template #default="{ row }">
              <span class="correct">{{ row.standard_answer || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="AI评分" width="90">
            <template #default="{ row }">
              <span :class="{ 'text-success': row.is_correct, 'text-danger': row.is_correct === false }">
                {{ row.score ?? '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="HR复核得分" width="100">
            <template #default="{ row }">
              <span v-if="detail.review_score !== null && detail.review_score !== undefined" class="text-warning">
                —
              </span>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="full_score" label="满分" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag
                v-if="row.score_level"
                :type="scoreLevelTagType(row.score_level)"
                size="small"
              >
                {{ scoreLevelText(row.score_level) }}
              </el-tag>
              <el-tag
                v-else-if="row.is_correct !== null && row.is_correct !== undefined"
                :type="row.is_correct ? 'success' : 'danger'"
                size="small"
              >
                {{ row.is_correct ? '正确' : '错误' }}
              </el-tag>
              <el-tag v-else type="info" size="small">未评分</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-empty v-else-if="errorMessage" :description="errorMessage" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { gradingResultApi } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const detail = ref(null)
const errorMessage = ref('')
const activeCollapse = ref([])

const reviewForm = reactive({
  review_score: null,
  review_comment: '',
})

const examRecordId = computed(() => parseInt(route.params.examRecordId))

// 计算最终显示分数：如果有HR复核分数，显示复核分数；否则显示系统总分
const finalScore = computed(() => {
  if (!detail.value) return 0
  if (detail.value.review_score !== null && detail.value.review_score !== undefined) {
    return detail.value.review_score
  }
  return detail.value.total_score || 0
})

// 计算最终及格状态
const finalPassed = computed(() => {
  if (!detail.value) return null
  if (detail.value.review_score !== null && detail.value.review_score !== undefined) {
    // 如果有复核分数，检查是否及格
    // 默认60分及格，或者使用原有的passed判断
    return detail.value.review_score >= 60
  }
  return detail.value.passed
})

// AI评分详情相关数据
const aiScoredAnswers = computed(() => {
  if (!detail.value || !detail.value.answers) return []
  return detail.value.answers.filter(a => a.ai_score !== null && a.ai_score !== undefined)
})

const aiConfidenceText = computed(() => {
  const aiAnswers = aiScoredAnswers.value
  if (aiAnswers.length === 0) return '-'
  const totalConfidence = aiAnswers.reduce((sum, a) => sum + (a.ai_confidence || 0), 0)
  const avgConfidence = totalConfidence / aiAnswers.length
  return (avgConfidence * 100).toFixed(1) + '%'
})

// 计算试卷总分（用于复核分数上限）
const maxScore = computed(() => {
  if (!detail.value || !detail.value.answers) return 100
  return detail.value.answers.reduce((sum, a) => sum + (a.full_score || 0), 0)
})

const statusText = (s) => ({ pending: '待评分', grading: '评分中', completed: '已完成', failed: '评分失败' }[s] || s)
const statusTagType = (s) => ({ pending: 'info', grading: 'warning', completed: 'success', failed: 'danger' }[s] || 'info')
const gradingTypeText = (t) => ({ auto: '自动', ai: 'AI', hybrid: '混合' }[t] || t)
const gradingTypeTag = (t) => ({ auto: '', ai: 'warning', hybrid: 'info' }[t] || '')
const questionTypeText = (t) => ({
  single_choice: '单选',
  multiple_choice: '多选',
  true_false: '判断',
  short_answer: '简答',
}[t] || t)

const scoreLevelText = (level) => ({
  full_correct: '完全正确',
  partial_correct: '部分正确',
  incorrect: '错误',
}[level] || '-')

const scoreLevelTagType = (level) => ({
  full_correct: 'success',
  partial_correct: 'warning',
  incorrect: 'danger',
}[level] || 'info')

function goBack() {
  router.push('/admin/grading')
}

function initReviewForm() {
  if (detail.value) {
    reviewForm.review_score = detail.value.review_score
    reviewForm.review_comment = detail.value.review_comment || ''
  }
}

function resetReviewForm() {
  initReviewForm()
  ElMessage.info('已重置为当前数据')
}

async function submitReview() {
  if (reviewForm.review_score === null || reviewForm.review_score === undefined) {
    ElMessage.warning('请输入复核分数')
    return
  }

  if (reviewForm.review_score < 0) {
    ElMessage.warning('复核分数不能为负数')
    return
  }

  if (reviewForm.review_score > maxScore.value) {
    ElMessage.warning(`复核分数不能超过试卷满分 ${maxScore.value}`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认保存HR复核分数 ${reviewForm.review_score} 分？保存后将作为最终成绩显示。`,
      '确认保存',
      {
        confirmButtonText: '确认保存',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    const res = await gradingResultApi.updateHRReview(examRecordId.value, {
      review_score: reviewForm.review_score,
      review_comment: reviewForm.review_comment,
    })
    detail.value = res.data
    ElMessage.success('HR复核保存成功')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

async function fetchDetail() {
  if (!examRecordId.value) {
    errorMessage.value = '无效的考试记录ID'
    loading.value = false
    return
  }

  loading.value = true
  try {
    const res = await gradingResultApi.getResultDetail(examRecordId.value)
    detail.value = res.data
    initReviewForm()
  } catch (e) {
    errorMessage.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.card-title {
  font-size: 14px;
  font-weight: 600;
}

.card-header-with-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-card {
  text-align: center;
  padding: 16px 0;
}

.score-card.final-score {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.score-detail {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.score-sub {
  font-size: 12px;
  color: #909399;
}

.score-status {
  margin-top: 8px;
}

.stat-card {
  text-align: center;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.option-item {
  font-size: 13px;
  color: #606266;
}

.option-label {
  font-weight: 600;
  margin-right: 4px;
}

.text-content {
  font-size: 13px;
  color: #606266;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.correct {
  color: #67c23a;
  font-weight: 500;
}

.wrong {
  color: #f56c6c;
}

.text-success {
  color: #67c23a;
  font-weight: 600;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.text-warning {
  color: #e6a23c;
  font-weight: 600;
}

.text-muted {
  color: #c0c4cc;
}

.pass {
  color: #67c23a;
}

.fail {
  color: #f56c6c;
}
</style>
