<template>
  <div class="exam-page">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <el-icon :size="48" class="is-loading"><Loading /></el-icon>
      <p>加载考试中...</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="error-state">
      <el-alert type="error" :closable="false">{{ error }}</el-alert>
      <el-button type="primary" @click="loadPaper">重试</el-button>
    </div>

    <!-- 已提交结果页 -->
    <div v-else-if="examStore.isSubmitted" class="result-page">
      <div class="result-card">
        <div class="result-header">
          <el-icon :size="64" class="success-icon"><CircleCheckFilled /></el-icon>
          <h2>考试已完成</h2>
          <p class="result-subtitle">您的答案已提交，等待批改</p>
        </div>
        
        <div class="result-stats">
          <div class="stat-item">
            <span class="stat-value">{{ examStore.answeredCount }}</span>
            <span class="stat-label">已答题数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ examStore.unansweredCount }}</span>
            <span class="stat-label">未答题数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ examStore.completionRate }}%</span>
            <span class="stat-label">完成率</span>
          </div>
        </div>

        <div class="result-info">
          <div class="info-row">
            <span class="info-label">候选人</span>
            <span class="info-value">{{ examStore.candidateName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">考试名称</span>
            <span class="info-value">{{ examStore.examInfo?.title }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">提交时间</span>
            <span class="info-value">{{ formatDateTime(submittedAt) }}</span>
          </div>
        </div>

        <div class="result-actions">
          <el-button type="primary" @click="goHome">返回首页</el-button>
        </div>
      </div>
    </div>

    <!-- 答题页面 -->
    <template v-else>
      <header class="exam-header">
        <div class="header-left">
          <h1 class="exam-title">{{ examStore.examInfo?.title }}</h1>
          <div class="exam-meta">
            <span v-if="examStore.examInfo?.durationMinutes">
              时长 {{ examStore.examInfo.durationMinutes }} 分钟
            </span>
            <span>{{ examStore.totalQuestions }} 题</span>
            <span>已答 {{ examStore.answeredCount }}/{{ examStore.totalQuestions }}</span>
          </div>
        </div>
        <div class="header-right">
          <div class="save-status" :class="`save-status--${examStore.saveStatus}`">
            <template v-if="examStore.saveStatus === 'saving'">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>保存中...</span>
            </template>
            <template v-else-if="examStore.saveStatus === 'saved'">
              <el-icon><CircleCheck /></el-icon>
              <span>已保存</span>
              <span v-if="examStore.lastSavedAt" class="save-time">
                {{ formatTime(examStore.lastSavedAt) }}
              </span>
            </template>
            <template v-else-if="examStore.saveStatus === 'error'">
              <el-icon><Warning /></el-icon>
              <span>保存失败</span>
              <el-button link type="primary" size="small" @click="handleRetry">
                重试
              </el-button>
            </template>
          </div>
          <span class="candidate-label">候选人</span>
          <span class="candidate-name">{{ examStore.candidateName }}</span>
        </div>
      </header>

      <div class="exam-body">
        <aside class="question-nav">
          <div class="nav-title">答题卡</div>
          <div class="nav-grid">
            <button
              v-for="(q, idx) in examStore.questions"
              :key="q.id"
              :class="[
                'nav-btn',
                { active: currentIndex === idx },
                { answered: isAnswered(q.id) },
              ]"
              @click="goToQuestion(idx)"
            >
              {{ idx + 1 }}
            </button>
          </div>
          <div class="nav-progress">
            <el-progress
              :percentage="examStore.completionRate"
              :stroke-width="8"
              :text-inside="true"
            />
            <span class="progress-label">完成率</span>
          </div>
          <div class="nav-legend">
            <span class="legend-item">
              <span class="legend-dot answered"></span>已答
            </span>
            <span class="legend-item">
              <span class="legend-dot current"></span>当前
            </span>
            <span class="legend-item">
              <span class="legend-dot"></span>未答
            </span>
          </div>
        </aside>

        <main class="question-main">
          <QuestionCard
            v-if="currentQuestion"
            :question="currentQuestion"
            :index="currentIndex"
            :answer="examStore.answers[currentQuestion.id]"
            :disabled="!examStore.canEdit"
            @update:answer="handleAnswer"
          />

          <div class="nav-actions">
            <el-button
              :disabled="currentIndex === 0"
              @click="prevQuestion"
            >
              上一题
            </el-button>
            <el-button
              v-if="currentIndex < examStore.questions.length - 1"
              type="primary"
              @click="nextQuestion"
            >
              下一题
            </el-button>
            <el-button
              v-else
              type="success"
              :loading="submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '提交中...' : '提交考试' }}
            </el-button>
          </div>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, CircleCheck, Warning, CircleCheckFilled } from '@element-plus/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useAutoSave } from '@/hooks/useAutoSave'
import QuestionCard from '@/components/exam/QuestionCard.vue'

const route = useRoute()
const router = useRouter()
const examStore = useExamStore()

const loading = ref(true)
const error = ref('')
const currentIndex = ref(0)
const recordId = ref(null)
const submitting = ref(false)
const submittedAt = ref(null)

const autoSave = useAutoSave(examStore)

const currentQuestion = computed(() => {
  return examStore.questions[currentIndex.value] || null
})

onMounted(async () => {
  recordId.value = route.params.id
  if (!recordId.value) {
    error.value = '考试记录ID无效'
    loading.value = false
    return
  }
  await loadPaper()
})

onBeforeUnmount(() => {
  autoSave.cleanup()
})

async function loadPaper() {
  loading.value = true
  error.value = ''
  try {
    // 1. 加载试卷
    await examStore.loadExamPaper(recordId.value)
    
    // 2. 如果状态是 not_started，自动开始考试
    if (examStore.status === 'not_started') {
      await examStore.startExam()
    }
    
    // 3. 如果已提交，直接显示结果
    if (examStore.isSubmitted) {
      submittedAt.value = examStore.examInfo?.submittedAt
      loading.value = false
      return
    }
    
    // 4. 加载历史答案（恢复进度）
    try {
      const historyAnswers = await examStore.loadHistoryAnswers()
      if (historyAnswers && historyAnswers.length > 0) {
        ElMessage.info(`已恢复 ${historyAnswers.length} 道题的答案`)
      }
    } catch (err) {
      console.warn('加载历史答案失败:', err)
    }
    
    loading.value = false
  } catch (err) {
    console.error('加载试卷失败:', err)
    error.value = '加载考试试卷失败，请重试'
    loading.value = false
  }
}

function isAnswered(questionId) {
  const ans = examStore.answers[questionId]
  if (ans === undefined || ans === null) return false
  if (Array.isArray(ans)) return ans.length > 0
  return ans !== ''
}

function handleAnswer(questionId, value) {
  if (!examStore.canEdit) return
  autoSave.saveCurrentAnswer(questionId, value)
}

async function goToQuestion(idx) {
  if (!examStore.canEdit) {
    currentIndex.value = idx
    return
  }
  await autoSave.flushSave()
  currentIndex.value = idx
}

async function prevQuestion() {
  if (!examStore.canEdit) {
    if (currentIndex.value > 0) currentIndex.value--
    return
  }
  if (currentIndex.value > 0) {
    await autoSave.flushSave()
    currentIndex.value--
  }
}

async function nextQuestion() {
  if (!examStore.canEdit) {
    if (currentIndex.value < examStore.questions.length - 1) currentIndex.value++
    return
  }
  if (currentIndex.value < examStore.questions.length - 1) {
    await autoSave.flushSave()
    currentIndex.value++
  }
}

async function handleSubmit() {
  if (submitting.value) return
  
  submitting.value = true
  
  try {
    // 1. 先保存所有答案
    const saved = await autoSave.saveAllAnswers()
    if (!saved) {
      ElMessage.error('答案保存失败，请检查网络后重试')
      submitting.value = false
      return
    }
    
    // 2. 确认对话框
    const unanswered = examStore.questions.filter(
      (q) => !isAnswered(q.id)
    ).length
    
    if (unanswered > 0) {
      try {
        await ElMessageBox.confirm(
          `您还有 ${unanswered} 道题未作答，确定要提交吗？提交后将无法修改。`,
          '提交确认',
          {
            confirmButtonText: '确定提交',
            cancelButtonText: '继续作答',
            type: 'warning',
          }
        )
      } catch {
        submitting.value = false
        return
      }
    } else {
      try {
        await ElMessageBox.confirm(
          '所有题目已作答，确定要提交吗？提交后将无法修改。',
          '提交确认',
          {
            confirmButtonText: '确定提交',
            cancelButtonText: '继续作答',
            type: 'success',
          }
        )
      } catch {
        submitting.value = false
        return
      }
    }
    
    // 3. 提交考试
    const result = await examStore.submitExam()
    submittedAt.value = result.submitted_at
    
    // 4. 跳转到结果页（由 isSubmitted getter 自动切换视图）
    ElMessage.success('考试提交成功！')
    
  } catch (err) {
    console.error('提交考试失败:', err)
    ElMessage.error(err.message || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function handleRetry() {
  const success = await autoSave.retrySave()
  if (success) {
    ElMessage.success('保存成功')
  } else {
    ElMessage.error('保存失败，请检查网络连接')
  }
}

function goHome() {
  router.push('/')
}

function formatTime(date) {
  if (!date) return ''
  const d = new Date(date)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  
  if (diff < 10) return '刚刚'
  if (diff < 60) return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function formatDateTime(date) {
  if (!date) return ''
  const d = new Date(date)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}
</script>

<style scoped>
.exam-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.loading-state,
.error-state {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #606266;
}

/* 结果页样式 */
.result-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.result-card {
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.result-header {
  margin-bottom: 32px;
}

.success-icon {
  color: #67c23a;
  margin-bottom: 16px;
}

.result-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.result-subtitle {
  color: #909399;
  margin: 0;
}

.result-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 32px;
  padding: 24px;
  background: #f5f7fa;
  border-radius: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: #e4e7ed;
}

.result-info {
  text-align: left;
  margin-bottom: 32px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: #909399;
  font-size: 14px;
}

.info-value {
  color: #303133;
  font-size: 14px;
  font-weight: 500;
}

.result-actions {
  display: flex;
  justify-content: center;
}

/* 答题页样式 */
.exam-header {
  background: #fff;
  padding: 16px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.exam-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.exam-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #909399;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 12px;
  transition: all 0.3s;
}

.save-status--saving {
  color: #409eff;
  background: #ecf5ff;
}

.save-status--saved {
  color: #67c23a;
  background: #f0f9eb;
}

.save-status--error {
  color: #f56c6c;
  background: #fef0f0;
}

.save-status .save-time {
  color: #909399;
  margin-left: 4px;
}

.candidate-label {
  font-size: 13px;
  color: #909399;
}

.candidate-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.exam-body {
  display: flex;
  gap: 24px;
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.question-nav {
  width: 200px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
  height: fit-content;
  position: sticky;
  top: 100px;
}

.nav-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.nav-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  color: #606266;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.nav-btn.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.nav-btn.answered:not(.active) {
  background: #e1f3d8;
  border-color: #e1f3d8;
  color: #67c23a;
}

.nav-progress {
  margin-bottom: 16px;
}

.progress-label {
  display: block;
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.nav-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #909399;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 1px solid #e4e7ed;
  background: #fff;
}

.legend-dot.answered {
  background: #e1f3d8;
  border-color: #e1f3d8;
}

.legend-dot.current {
  background: #409eff;
  border-color: #409eff;
}

.question-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.nav-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 0 8px;
}
</style>
