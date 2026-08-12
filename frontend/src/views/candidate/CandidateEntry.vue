<template>
  <div class="candidate-entry-page">
    <div class="entry-card">
      <!-- 状态 1: 输入考试码 -->
      <template v-if="step === 1">
        <div class="entry-header">
          <div class="logo-icon">
            <el-icon :size="40" color="#409eff"><Document /></el-icon>
          </div>
          <h1 class="entry-title">AI 智能考试系统</h1>
          <p class="entry-subtitle">请输入考试访问码开始答题</p>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-position="top"
          class="entry-form"
        >
          <el-form-item label="考试访问码" prop="exam_code">
            <el-input
              v-model="formData.exam_code"
              placeholder="请输入考试访问码"
              size="large"
              maxlength="50"
              clearable
            >
              <template #prefix>
                <el-icon><Key /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </el-form>

        <el-button
          type="primary"
          size="large"
          class="start-btn"
          :loading="loading"
          @click="handleVerify"
        >
          验证考试码
        </el-button>
      </template>

      <!-- 状态 2: 显示考试信息 + 填写候选人信息 -->
      <template v-else-if="step === 2">
        <div class="exam-info">
          <div class="info-header">
            <el-tag type="success" size="large" effect="dark">已验证</el-tag>
            <h2 class="exam-name">{{ examInfo.title }}</h2>
            <p class="exam-desc" v-if="examInfo.description">{{ examInfo.description }}</p>
          </div>
          <div class="info-meta">
            <div class="meta-item" v-if="examInfo.duration_minutes">
              <el-icon><Clock /></el-icon>
              <span>时长 {{ examInfo.duration_minutes }} 分钟</span>
            </div>
            <div class="meta-item" v-if="examInfo.question_count">
              <el-icon><Tickets /></el-icon>
              <span>共 {{ examInfo.question_count }} 题</span>
            </div>
            <div class="meta-item" v-if="examInfo.pass_score">
              <el-icon><Medal /></el-icon>
              <span>及格 {{ examInfo.pass_score }} 分</span>
            </div>
          </div>
        </div>

        <el-divider />

        <div class="candidate-form">
          <h3 class="form-title">填写候选人信息</h3>
          <el-form
            ref="candidateFormRef"
            :model="candidateForm"
            :rules="candidateRules"
            label-position="top"
          >
            <el-form-item label="候选人姓名" prop="candidate_name">
              <el-input
                v-model="candidateForm.candidate_name"
                placeholder="请输入您的姓名"
                size="large"
                maxlength="64"
              />
            </el-form-item>

            <el-form-item label="联系手机" prop="candidate_phone">
              <el-input
                v-model="candidateForm.candidate_phone"
                placeholder="请输入手机号码（用于身份验证）"
                size="large"
                maxlength="20"
              />
            </el-form-item>

            <el-form-item label="电子邮箱" prop="candidate_email">
              <el-input
                v-model="candidateForm.candidate_email"
                placeholder="请输入邮箱地址（选填）"
                size="large"
                maxlength="128"
              />
            </el-form-item>
          </el-form>
        </div>

        <div class="button-group">
          <el-button
            size="large"
            @click="step = 1"
          >
            返回
          </el-button>
          <el-button
            type="primary"
            size="large"
            class="start-btn"
            :loading="submitting"
            @click="handleStart"
          >
            开始考试
          </el-button>
        </div>
      </template>

      <!-- 状态 3: 成功创建考试记录 -->
      <template v-else-if="step === 3">
        <div class="success-state">
          <el-icon :size="64" color="#67c23a"><CircleCheckFilled /></el-icon>
          <h2 class="success-title">考试记录创建成功</h2>
          <p class="success-desc">您的考试记录已创建，请点击下方按钮开始答题</p>

          <el-descriptions :column="1" border class="record-info">
            <el-descriptions-item label="考试名称">
              {{ examInfo.title }}
            </el-descriptions-item>
            <el-descriptions-item label="候选人">
              {{ candidateForm.candidate_name }}
            </el-descriptions-item>
            <el-descriptions-item label="记录编号">
              {{ recordId }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag type="info" size="small">待开始</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-button
            type="primary"
            size="large"
            class="start-btn"
            @click="goToExam"
          >
            开始答题
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Document,
  Key,
  Clock,
  Tickets,
  Medal,
  CircleCheckFilled,
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()

const formRef = ref(null)
const candidateFormRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const step = ref(1)
const examInfo = ref({})
const recordId = ref(null)

const formData = reactive({
  exam_code: '',
})

const candidateForm = reactive({
  candidate_name: '',
  candidate_phone: '',
  candidate_email: '',
})

const rules = {
  exam_code: [
    { required: true, message: '请输入考试访问码', trigger: 'blur' },
    { min: 1, max: 50, message: '访问码长度 1-50 个字符', trigger: 'blur' },
  ],
}

const candidateRules = {
  candidate_name: [
    { required: true, message: '请输入候选人姓名', trigger: 'blur' },
    { min: 1, max: 64, message: '姓名长度 1-64 个字符', trigger: 'blur' },
  ],
  candidate_phone: [
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入正确的手机号码',
      trigger: 'blur',
    },
  ],
  candidate_email: [
    {
      type: 'email',
      message: '请输入正确的邮箱地址',
      trigger: 'blur',
    },
  ],
}

async function handleVerify() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await request.get('/exams/entry/by-code', {
      params: { exam_code: formData.exam_code },
    })
    examInfo.value = res.data
    step.value = 2
    ElMessage.success('考试码验证成功')
  } catch (err) {
    // 错误信息已通过 Axios 拦截器显示给用户
  } finally {
    loading.value = false
  }
}

async function handleStart() {
  try {
    await candidateFormRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const res = await request.post('/exam-records', {
      exam_id: examInfo.value.id,
      exam_code: formData.exam_code,
      candidate_name: candidateForm.candidate_name,
      candidate_phone: candidateForm.candidate_phone || null,
      candidate_email: candidateForm.candidate_email || null,
    })
    recordId.value = res.data.id
    step.value = 3
    ElMessage.success('身份验证成功，正在进入考试...')
  } catch (err) {
    console.error('创建考试记录失败:', err)
  } finally {
    submitting.value = false
  }
}

function goToExam() {
  router.push(`/exam/record/${recordId.value}`)
}
</script>

<style scoped>
.candidate-entry-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.entry-card {
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.entry-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.entry-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.entry-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.entry-form {
  margin-bottom: 24px;
}

.start-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
}

/* 步骤 2: 考试信息 */
.exam-info {
  text-align: center;
}

.info-header {
  margin-bottom: 16px;
}

.exam-name {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 12px 0 8px;
}

.exam-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
  line-height: 1.6;
}

.info-meta {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.candidate-form {
  margin-bottom: 24px;
}

.form-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 16px;
}

.button-group {
  display: flex;
  gap: 12px;
}

.button-group .start-btn {
  flex: 1;
}

/* 步骤 3: 成功状态 */
.success-state {
  text-align: center;
}

.success-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 16px 0 8px;
}

.success-desc {
  font-size: 14px;
  color: #909399;
  margin: 0 0 24px;
}

.record-info {
  margin-bottom: 24px;
  text-align: left;
}

:deep(.el-divider__text) {
  background: transparent;
}
</style>
