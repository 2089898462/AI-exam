<template>
  <div class="exam-page">
    <div v-if="loading" class="loading-state">
      <el-icon :size="48" class="is-loading"><Loading /></el-icon>
      <p>加载考试中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <el-alert type="error" :closable="false">{{ error }}</el-alert>
      <el-button type="primary" @click="loadPaper">重试</el-button>
    </div>

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
              @click="handleFinish"
            >
              完成
            </el-button>
          </div>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useExamStore } from '@/stores/exam'
import QuestionCard from '@/components/exam/QuestionCard.vue'

const route = useRoute()
const router = useRouter()
const examStore = useExamStore()

const loading = ref(true)
const error = ref('')
const currentIndex = ref(0)
const recordId = ref(null)

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

async function loadPaper() {
  loading.value = true
  error.value = ''
  try {
    await examStore.loadExamPaper(recordId.value)
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
  examStore.setAnswer(questionId, value)
}

function goToQuestion(idx) {
  currentIndex.value = idx
}

function prevQuestion() {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

function nextQuestion() {
  if (currentIndex.value < examStore.questions.length - 1) {
    currentIndex.value++
  }
}

async function handleFinish() {
  const unanswered = examStore.questions.filter(
    (q) => !isAnswered(q.id)
  ).length

  if (unanswered > 0) {
    try {
      await ElMessageBox.confirm(
        `您还有 ${unanswered} 道题未作答，确定要完成吗？`,
        '提示',
        {
          confirmButtonText: '确定完成',
          cancelButtonText: '继续作答',
          type: 'warning',
        }
      )
    } catch {
      return
    }
  }

  ElMessage.success('考试完成！')
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
  gap: 8px;
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
