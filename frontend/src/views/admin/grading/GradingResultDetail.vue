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

      <!-- 评分结果卡片 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="8">
          <el-card class="score-card">
            <el-statistic
              title="总分"
              :value="detail.total_score || 0"
              :precision="1"
              :class="{ 'pass': detail.passed, 'fail': detail.passed === false }"
            />
            <div class="score-status">
              <el-tag v-if="detail.passed !== null && detail.passed !== undefined" :type="detail.passed ? 'success' : 'danger'" size="large">
                {{ detail.passed ? '及格' : '不及格' }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="score-card">
            <el-statistic title="客观题得分" :value="detail.auto_score || 0" :precision="1" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="score-card">
            <el-statistic title="AI评分得分" :value="detail.ai_score || 0" :precision="1" />
          </el-card>
        </el-col>
      </el-row>

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
          <el-table-column prop="score" label="得分" width="80">
            <template #default="{ row }">
              <span :class="{ 'text-success': row.is_correct, 'text-danger': row.is_correct === false }">
                {{ row.score ?? '-' }}
              </span>
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
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { gradingResultApi } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const detail = ref(null)
const errorMessage = ref('')

const examRecordId = computed(() => parseInt(route.params.examRecordId))

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

.score-card {
  text-align: center;
  padding: 20px 0;
}

.score-status {
  margin-top: 10px;
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

.pass {
  color: #67c23a;
}

.fail {
  color: #f56c6c;
}
</style>
