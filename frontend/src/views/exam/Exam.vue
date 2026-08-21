<template>
  <div class="exam-page" :class="{ 'is-mobile': isMobile }">
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
      <!-- 顶部信息栏 -->
      <header class="exam-header">
        <div class="header-main">
          <h1 class="exam-title">{{ examStore.examInfo?.title }}</h1>
          <div class="header-info">
            <span class="info-item">
              {{ currentIndex + 1 }} / {{ examStore.totalQuestions }}
            </span>
            <span
              class="timer-display"
              :class="{ 'timer-warning': isTimeWarning, 'timer-danger': isTimeDanger }"
            >
              <el-icon><Clock /></el-icon>
              {{ formattedRemainingTime }}
            </span>
          </div>
        </div>
        <div class="header-side">
          <div class="save-status" :class="`save-status--${examStore.saveStatus}`">
            <template v-if="examStore.saveStatus === 'saving'">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span class="save-label">保存中</span>
            </template>
            <template v-else-if="examStore.saveStatus === 'saved'">
              <el-icon><CircleCheck /></el-icon>
              <span class="save-label">已保存</span>
            </template>
            <template v-else-if="examStore.saveStatus === 'error'">
              <el-icon><Warning /></el-icon>
              <span class="save-label">保存失败</span>
            </template>
          </div>
          <span class="candidate-name">{{ examStore.candidateName }}</span>
        </div>
      </header>

      <!-- 桌面端侧边栏 -->
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
        </main>
      </div>

      <!-- 底部操作栏（移动端固定） -->
      <nav class="bottom-bar">
        <button class="bar-btn bar-btn--nav" @click="showAnswerSheet = true">
          <el-icon><Grid /></el-icon>
          <span>答题卡</span>
        </button>
        <button
          class="bar-btn bar-btn--prev"
          :disabled="currentIndex === 0"
          @click="prevQuestion"
        >
          <el-icon><ArrowLeft /></el-icon>
          <span>上一题</span>
        </button>
        <button
          v-if="currentIndex < examStore.questions.length - 1"
          class="bar-btn bar-btn--next"
          @click="nextQuestion"
        >
          <span>下一题</span>
          <el-icon><ArrowRight /></el-icon>
        </button>
        <button
          v-else
          class="bar-btn bar-btn--submit"
          :disabled="submitting"
          @click="handleSubmit"
        >
          <el-icon v-if="!submitting"><Finished /></el-icon>
          <span>{{ submitting ? '提交中...' : '提交试卷' }}</span>
        </button>
      </nav>

      <!-- 移动端答题卡弹层 -->
      <transition name="sheet">
        <div v-if="showAnswerSheet" class="answer-sheet-mask" @click="showAnswerSheet = false">
          <div class="answer-sheet" @click.stop>
            <div class="sheet-header">
              <span>答题卡</span>
              <el-icon @click="showAnswerSheet = false"><Close /></el-icon>
            </div>
            <div class="sheet-progress">
              <el-progress :percentage="examStore.completionRate" :stroke-width="10" />
              <span class="sheet-progress-label">
                已答 {{ examStore.answeredCount }}/{{ examStore.totalQuestions }}
              </span>
            </div>
            <div class="sheet-nav-grid">
              <button
                v-for="(q, idx) in examStore.questions"
                :key="q.id"
                :class="[
                  'sheet-nav-btn',
                  { active: currentIndex === idx },
                  { answered: isAnswered(q.id) },
                ]"
                @click="goToQuestionFromSheet(idx)"
              >
                {{ idx + 1 }}
              </button>
            </div>
            <div class="sheet-legend">
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
            <div class="sheet-footer">
              <button
                v-if="currentIndex < examStore.questions.length - 1"
                class="sheet-submit-btn"
                :disabled="submitting"
                @click="handleSubmit"
              >
                {{ submitting ? '提交中...' : '提交试卷' }}
              </button>
              <div v-else class="sheet-submit-wrap">
                <button
                  class="sheet-submit-btn sheet-submit-btn--primary"
                  :disabled="submitting"
                  @click="handleSubmit"
                >
                  {{ submitting ? '提交中...' : '提交试卷' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, CircleCheck, Warning, CircleCheckFilled, Clock, Grid, ArrowLeft, ArrowRight, Finished, Close } from '@element-plus/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useAutoSave } from '@/hooks/useAutoSave'
import { useMonitor } from '@/hooks/useMonitor'
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

// 倒计时相关（S8.4.4: 基于服务器时间校准，刷新/切后台不重置）
const startTime = ref(null)
const remainingSeconds = ref(0)
let countdownTimer = null
// 服务器时钟偏差：serverNow = Date.now() - clockOffsetMs
let clockOffsetMs = 0
// 考试开始时间（服务器时钟基准，毫秒）
let examStartedAtMs = null

// 移动端检测
const isMobile = ref(false)
const showAnswerSheet = ref(false)

const autoSave = useAutoSave(examStore)
const monitor = useMonitor()

const currentQuestion = computed(() => {
  return examStore.questions[currentIndex.value] || null
})

const totalDurationSeconds = computed(() => {
  return (examStore.examInfo?.durationMinutes || 0) * 60
})

const formattedRemainingTime = computed(() => {
  const total = Math.max(0, remainingSeconds.value)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const isTimeWarning = computed(() => {
  return remainingSeconds.value > 0 && remainingSeconds.value <= 300
})

const isTimeDanger = computed(() => {
  return remainingSeconds.value > 0 && remainingSeconds.value <= 60
})

function checkMobile() {
  isMobile.value = window.innerWidth <= 768
}

/**
 * 服务器当前时间（毫秒，经时钟偏差校准）
 */
function serverNow() {
  return Date.now() - clockOffsetMs
}

/**
 * S8.4.4: 基于服务器时间的倒计时
 *
 * 真实剩余时间 = 考试开始时间 + 总考试时长 - 当前服务器时间
 *
 * - startedAt: 考试真实开始时间（服务器时钟，in_progress 状态下由 paper 接口返回）
 * - serverTime: 服务器当前时间（用于校准客户端时钟偏差，防止用户修改系统时间）
 *
 * 刷新页面 → 重新拉取 paper 接口 → 恢复真实剩余时间（不再从满时长开始）
 */
function startCountdown(startedAt = null, serverTime = null) {
  stopCountdown()

  // 校准时钟偏差（本地时间 - 服务器时间）
  if (serverTime) {
    clockOffsetMs = Date.now() - new Date(serverTime).getTime()
  }

  // 设置考试开始时间基准
  if (startedAt) {
    examStartedAtMs = new Date(startedAt).getTime()
  }

  if (examStartedAtMs == null) {
    // 兜底：未获取到开始时间（如首次开始考试的瞬间），以校准后的服务器当前时间为准
    console.warn('[Exam] 未获取到 started_at，以当前服务器时间作为考试开始基准')
    examStartedAtMs = serverNow()
  }

  startTime.value = new Date(examStartedAtMs)
  refreshRemainingTime()

  countdownTimer = setInterval(refreshRemainingTime, 1000)
}

/**
 * 刷新剩余时间（每秒执行；切后台返回时也会立即调用）
 * 基于锚点计算，后台经过的时间会被正确扣除，不会重置
 */
function refreshRemainingTime() {
  if (examStartedAtMs == null) return

  const elapsedMs = serverNow() - examStartedAtMs
  const remaining = Math.max(0, Math.ceil((totalDurationSeconds.value * 1000 - elapsedMs) / 1000))
  remainingSeconds.value = remaining

  // 时间到自动提交
  if (remaining === 0 && examStore.canEdit) {
    handleSubmit()
  }
}

/**
 * S8.4.4: 切后台返回时立即校准倒计时显示
 * 移动端浏览器后台会冻结/节流定时器，返回后需立即刷新（计算本身基于锚点，后台时间已正确扣除）
 */
function handleVisibilityForCountdown() {
  if (document.visibilityState === 'visible') {
    refreshRemainingTime()
  }
}

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  // S8.4.4: 切后台返回时立即校准倒计时显示
  document.addEventListener('visibilitychange', handleVisibilityForCountdown)

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
  monitor.stopMonitoring()
  stopCountdown()
  window.removeEventListener('resize', checkMobile)
  document.removeEventListener('visibilitychange', handleVisibilityForCountdown)
})

async function loadPaper() {
  loading.value = true
  error.value = ''
  try {
    // S8.4.4: paper 接口返回 started_at / server_time，用于倒计时恢复
    const paper = await examStore.loadExamPaper(recordId.value)

    if (examStore.status === 'not_started') {
      // S8.4.7: 正式开始考试前弹出诚信考试警示弹窗（威慑提示）
      // 弹窗不可关闭：考生必须点击"我已知悉，开始考试"后考试才会真正开始
      await ElMessageBox.confirm(
        `<div style="text-align:left; line-height:2; font-size:14px; color:#303133;">
           <p style="margin:0 0 8px;">本场考试全程由 <b>智能监考系统实时监测</b>，请遵守以下考试纪律：</p>
           <p style="margin:0;">1. 请勿<b>切换屏幕</b>、锁屏或离开考试页面；</p>
           <p style="margin:0;">2. 请勿使用<b>小窗、分屏、悬浮窗</b>或手机/电脑上的搜索、AI 等工具查询答案；</p>
           <p style="margin:0;">3. 切屏、离开页面等行为将被系统<b>自动记录</b>，并作为作弊判定依据提交人工审核；</p>
           <p style="margin:8px 0 0;">4. 请在安静、无干扰的环境中<b>独立完成</b>全部作答。</p>
         </div>`,
        '考试诚信承诺提示',
        {
          confirmButtonText: '我已知悉，开始考试',
          showCancelButton: false,
          showClose: false,
          closeOnClickModal: false,
          closeOnPressEscape: false,
          type: 'warning',
          dangerouslyUseHTMLString: true,
          customClass: 'exam-integrity-box',
        }
      )
      // 首次开始考试：startExam 返回的记录含 started_at（服务器写入的真实开始时间）
      const record = await examStore.startExam()
      monitor.startMonitoring(recordId.value)
      startCountdown(record?.started_at || paper?.started_at, paper?.server_time)
    } else if (examStore.status === 'in_progress') {
      // 断点恢复：使用服务器返回的 started_at 恢复真实剩余时间
      monitor.startMonitoring(recordId.value)
      startCountdown(paper?.started_at, paper?.server_time)
    }
    
    if (examStore.isSubmitted) {
      submittedAt.value = examStore.examInfo?.submittedAt
      loading.value = false
      return
    }
    
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

function goToQuestionFromSheet(idx) {
  showAnswerSheet.value = false
  goToQuestion(idx)
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
    const saved = await autoSave.saveAllAnswers()
    if (!saved) {
      ElMessage.error('答案保存失败，请检查网络后重试')
      submitting.value = false
      return
    }
    
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
    
    const monitorData = monitor.flushEvents()
    const result = await examStore.submitExam(monitorData)
    submittedAt.value = result.submitted_at

    monitor.stopMonitoring()
    // S8.4.4: 提交成功后清除监考缓存，避免重进时重复累计；提交失败则保留缓存
    monitor.clearPersistedData()
    stopCountdown()
    
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
/* ==================== 基础样式 ==================== */
.exam-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 72px;
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

/* ==================== 结果页 ==================== */
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

/* ==================== 顶部信息栏 ==================== */
.exam-header {
  background: #fff;
  padding: 14px 20px;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.exam-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.info-item {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.timer-display {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  padding: 4px 10px;
  background: #f0f2f5;
  border-radius: 6px;
  font-variant-numeric: tabular-nums;
}

.timer-display.timer-warning {
  color: #e6a23c;
  background: #fdf6ec;
}

.timer-display.timer-danger {
  color: #f56c6c;
  background: #fef0f0;
  animation: timer-pulse 1s ease-in-out infinite;
}

@keyframes timer-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.header-side {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.save-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
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

.save-label {
  font-size: 12px;
}

.candidate-name {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

/* ==================== 桌面端布局 ==================== */
.exam-body {
  display: flex;
  gap: 24px;
  padding: 24px 20px;
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
  min-width: 0;
}

/* ==================== 底部操作栏 ==================== */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  padding-bottom: calc(10px + env(safe-area-inset-bottom));
  z-index: 20;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.bar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  padding: 10px 14px;
  min-height: 44px;
  color: #606266;
}

.bar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.bar-btn:not(:disabled):active {
  transform: scale(0.96);
}

.bar-btn--nav {
  color: #409eff;
  flex-direction: column;
  font-size: 11px;
  padding: 6px 10px;
  min-width: 52px;
  min-height: 48px;
}

.bar-btn--nav .el-icon {
  font-size: 18px;
}

.bar-btn--prev {
  color: #606266;
}

.bar-btn--next {
  color: #409eff;
}

.bar-btn--submit {
  background: #409eff;
  color: #fff;
  min-width: 120px;
}

.bar-btn--submit:not(:disabled):active {
  background: #337ecc;
}

/* ==================== 答题卡弹层 ==================== */
.answer-sheet-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 30;
  display: flex;
  align-items: flex-end;
}

.answer-sheet {
  width: 100%;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 20px 16px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  max-height: 80vh;
  overflow-y: auto;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.sheet-header .el-icon {
  font-size: 20px;
  cursor: pointer;
  color: #909399;
}

.sheet-progress {
  margin-bottom: 20px;
}

.sheet-progress-label {
  display: block;
  text-align: center;
  font-size: 13px;
  color: #606266;
  margin-top: 6px;
}

.sheet-nav-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.sheet-nav-btn {
  width: 100%;
  aspect-ratio: 1;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  color: #606266;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.sheet-nav-btn.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.sheet-nav-btn.answered:not(.active) {
  background: #e1f3d8;
  border-color: #c2e7b0;
  color: #67c23a;
}

.sheet-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 20px;
  font-size: 13px;
  color: #909399;
}

.sheet-footer {
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.sheet-submit-wrap {
  display: flex;
  justify-content: center;
}

.sheet-submit-btn {
  width: 100%;
  max-width: 320px;
  padding: 14px;
  border: none;
  border-radius: 12px;
  background: #f5f7fa;
  color: #606266;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.sheet-submit-btn.sheet-submit-btn--primary {
  background: #409eff;
  color: #fff;
}

.sheet-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==================== Sheet 动画 ==================== */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.3s ease;
}

.sheet-enter-active .answer-sheet,
.sheet-leave-active .answer-sheet {
  transition: transform 0.3s ease;
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}

.sheet-enter-from .answer-sheet,
.sheet-leave-to .answer-sheet {
  transform: translateY(100%);
}

/* ==================== 移动端适配 ==================== */
@media (max-width: 768px) {
  .exam-page.is-mobile {
    padding-bottom: 64px;
  }

  /* 顶部 */
  .exam-header {
    padding: 12px 16px;
  }

  .header-main {
    gap: 8px;
    margin-bottom: 6px;
  }

  .exam-title {
    font-size: 15px;
  }

  .header-info {
    gap: 8px;
  }

  .info-item {
    font-size: 13px;
  }

  .timer-display {
    font-size: 13px;
    padding: 3px 8px;
  }

  .header-side {
    justify-content: space-between;
  }

  .save-status {
    font-size: 11px;
  }

  .save-label {
    display: none;
  }

  .candidate-name {
    font-size: 12px;
  }

  /* 隐藏桌面侧边栏 */
  .exam-body {
    padding: 16px;
    gap: 0;
  }

  .question-nav {
    display: none;
  }

  .question-main {
    width: 100%;
  }

  /* 显示底部操作栏 */
  .bottom-bar {
    display: flex;
  }

  .bar-btn--nav {
    display: inline-flex;
  }

  /* 结果页 */
  .result-card {
    padding: 28px 20px;
  }

  .result-stats {
    gap: 16px;
    padding: 16px;
  }

  .stat-value {
    font-size: 22px;
  }
}

@media (max-width: 380px) {
  .header-main {
    flex-wrap: wrap;
  }

  .exam-title {
    font-size: 14px;
  }

  .bar-btn {
    font-size: 14px;
    padding: 8px 10px;
  }

  .bar-btn--submit {
    min-width: 100px;
  }

  .sheet-nav-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}
</style>

<style>
/* S8.4.7: 诚信考试警示弹窗移动端适配（ElMessageBox 挂载在 body，需全局样式） */
@media (max-width: 480px) {
  .el-message-box.exam-integrity-box {
    width: 88% !important;
  }
  .el-message-box.exam-integrity-box .el-message-box__btns .el-button {
    /* 移动端触摸目标 ≥44px */
    min-height: 44px;
    padding: 12px 20px;
  }
}
</style>
