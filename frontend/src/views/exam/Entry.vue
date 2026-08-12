<template>
  <div class="entry-page">
    <div class="entry-card">
      <!-- 成功状态 -->
      <template v-if="isSubmitted">
        <div class="success-state">
          <div class="success-icon">
            <el-icon :size="64" color="#67c23a"><CircleCheckFilled /></el-icon>
          </div>
          <h2 class="success-title">考试记录创建成功</h2>
          <p class="success-desc">您的考试记录已创建，请点击下方按钮开始答题</p>
          <el-descriptions :column="1" border class="record-info">
            <el-descriptions-item label="考试名称">
              {{ examTitle }}
            </el-descriptions-item>
            <el-descriptions-item label="候选人">
              {{ formData.candidate_name }}
            </el-descriptions-item>
            <el-descriptions-item label="记录编号">
              {{ examStore.recordId }}
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

      <!-- 表单状态 -->
      <template v-else>
        <div class="entry-header">
          <h1 class="exam-title">{{ examTitle }}</h1>
          <p class="exam-desc" v-if="examDescription">{{ examDescription }}</p>
          <div class="exam-meta" v-if="examInfo">
            <span v-if="examInfo.duration_minutes">时长 {{ examInfo.duration_minutes }} 分钟</span>
            <span v-if="examInfo.question_count">共 {{ examInfo.question_count }} 题</span>
            <span v-if="examInfo.pass_score">及格 {{ examInfo.pass_score }} 分</span>
          </div>
        </div>

        <el-divider />

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-position="top"
          class="entry-form"
        >
          <el-form-item label="考试凭证" prop="exam_code">
            <el-input
              v-model="formData.exam_code"
              placeholder="请输入考试访问码"
              size="large"
              maxlength="50"
            />
          </el-form-item>

          <el-form-item label="候选人姓名" prop="candidate_name">
            <el-input
              v-model="formData.candidate_name"
              placeholder="请输入您的姓名"
              size="large"
              maxlength="64"
            />
          </el-form-item>

          <el-form-item label="联系手机" prop="candidate_phone">
            <el-input
              v-model="formData.candidate_phone"
              placeholder="请输入手机号码（用于身份验证）"
              size="large"
              maxlength="20"
            />
          </el-form-item>

          <el-form-item label="电子邮箱" prop="candidate_email">
            <el-input
              v-model="formData.candidate_email"
              placeholder="请输入邮箱地址（选填）"
              size="large"
              maxlength="128"
            />
          </el-form-item>
        </el-form>

        <el-button
          type="primary"
          size="large"
          class="start-btn"
          :loading="loading"
          @click="handleStart"
        >
          开始考试
        </el-button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled } from '@element-plus/icons-vue'
import { examRecordApi } from '@/api/examRecord'
import { useExamStore } from '@/stores/exam'

const route = useRoute()
const router = useRouter()
const examStore = useExamStore()

const formRef = ref(null)
const loading = ref(false)
const isSubmitted = ref(false)
const examId = ref(null)
const examTitle = ref('')
const examDescription = ref('')
const examInfo = ref(null)

const formData = reactive({
  exam_code: '',
  candidate_name: '',
  candidate_phone: '',
  candidate_email: '',
})

const rules = {
  exam_code: [
    { required: true, message: '请输入考试凭证', trigger: 'blur' },
    { min: 1, max: 50, message: '凭证长度 1-50 个字符', trigger: 'blur' },
  ],
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

onMounted(async () => {
  examId.value = route.params.id
  if (!examId.value) {
    ElMessage.error('考试ID无效')
    router.replace('/')
    return
  }
  try {
    const res = await examRecordApi.getExamInfo(examId.value)
    examInfo.value = res.data
    examTitle.value = res.data.title || '考试'
    examDescription.value = res.data.description || ''
  } catch {
    examTitle.value = '考试'
  }
})

async function handleStart() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await examStore.createRecord({
      exam_id: examId.value,
      exam_code: formData.exam_code,
      candidate_name: formData.candidate_name,
      candidate_phone: formData.candidate_phone || null,
      candidate_email: formData.candidate_email || null,
    })
    ElMessage.success('身份验证成功，正在进入考试...')
    isSubmitted.value = true
  } catch (err) {
    console.error('创建考试记录失败:', err)
    // 错误信息已通过 Axios 拦截器显示给用户
  } finally {
    loading.value = false
  }
}

function goToExam() {
  router.push(`/exam/record/${examStore.recordId}`)
}
</script>

<style scoped>
.entry-page {
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
  margin-bottom: 8px;
}

.exam-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.exam-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
  line-height: 1.6;
}

.exam-meta {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 16px;
  font-size: 13px;
  color: #606266;
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

.success-state {
  text-align: center;
}

.success-icon {
  margin-bottom: 16px;
}

.success-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
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
