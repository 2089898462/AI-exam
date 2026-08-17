<template>
  <div class="exam-detail">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button @click="goBack" link>
              <el-icon><ArrowLeft /></el-icon>
              返回列表
            </el-button>
            <span class="title">{{ exam.title || '考试详情' }}</span>
            <el-tag :type="statusTagType(exam.status)" style="margin-left: 12px">
              {{ statusText(exam.status) }}
            </el-tag>
          </div>
          <div class="header-right">
            <el-button
              type="success"
              :disabled="!canEdit"
              @click="openFormDialog()"
            >
              <el-icon><Plus /></el-icon>
              添加题目
            </el-button>
            <el-button
              type="primary"
              :disabled="!canImport"
              @click="showImportDialog = true"
            >
              <el-icon><Upload /></el-icon>
              导入试卷
            </el-button>
            <el-button
              v-if="exam.status === 'published'"
              type="warning"
              @click="handleClose"
            >关闭考试</el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="3" border v-if="exam.id">
        <el-descriptions-item label="考试 ID">{{ exam.id }}</el-descriptions-item>
        <el-descriptions-item label="考试名称">{{ exam.title }}</el-descriptions-item>
        <el-descriptions-item label="考试编码">{{ exam.exam_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="岗位">{{ exam.position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="考试时长">{{ exam.duration_minutes }} 分钟</el-descriptions-item>
        <el-descriptions-item label="及格分数">{{ exam.pass_score }}</el-descriptions-item>
        <el-descriptions-item label="题目数量">{{ exam.question_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="考试状态">{{ statusText(exam.status) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ exam.created_at }}</el-descriptions-item>
        <el-descriptions-item label="发布时间" v-if="exam.published_at">{{ exam.published_at }}</el-descriptions-item>
        <el-descriptions-item label="关闭时间" v-if="exam.closed_at">{{ exam.closed_at }}</el-descriptions-item>
        <el-descriptions-item label="考试说明" :span="3">
          {{ exam.description || '无' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-tabs v-model="activeTab" style="margin-top: 16px">
        <el-tab-pane label="题目列表" name="questions">
          <QuestionTable
            :exam-id="exam.id"
            :questions="exam.questions || []"
            :readonly="!canEdit"
            @delete="handleQuestionDelete"
            @edit="handleQuestionEdit"
          />
        </el-tab-pane>
        <el-tab-pane label="参与人员" name="participants">
          <ExamParticipants :exam-id="exam.id" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <ImportExamDialog
      v-model="showImportDialog"
      :exam-id="exam.id"
      @success="handleImportSuccess"
    />

    <QuestionFormDialog
      v-model="showFormDialog"
      :exam-id="exam.id"
      :edit-data="editingQuestion"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Upload, Plus } from '@element-plus/icons-vue'
import { examApi } from '@/api'
import ImportExamDialog from '@/components/exam/ImportExamDialog.vue'
import QuestionFormDialog from '@/components/exam/QuestionFormDialog.vue'
import QuestionTable from '@/components/exam/QuestionTable.vue'
import ExamParticipants from './ExamParticipants.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const exam = ref({})
const showImportDialog = ref(false)
const showFormDialog = ref(false)
const editingQuestion = ref(null)
const activeTab = ref('questions')

const statusText = (s) => ({ draft: '草稿', published: '已发布', closed: '已关闭' }[s] || s)
const statusTagType = (s) => ({ draft: 'info', published: 'success', closed: 'danger' }[s] || 'info')

const canImport = computed(() => exam.value.status === 'draft')
const canEdit = computed(() => exam.value.status === 'draft')

async function loadDetail() {
  loading.value = true
  try {
    const res = await examApi.getExamDetail(route.params.id)
    exam.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleClose() {
  try {
    await ElMessageBox.confirm('确定关闭此考试吗？关闭后考生将无法参加。', '关闭确认', {
      type: 'warning',
    })
    await examApi.closeExam(route.params.id)
    ElMessage.success('已关闭')
    loadDetail()
  } catch (e) {
    /* cancelled */
  }
}

function handleImportSuccess() {
  showImportDialog.value = false
  loadDetail()
}

function openFormDialog() {
  console.log('[DEBUG] openFormDialog called')
  console.log('[DEBUG] canEdit:', canEdit.value, 'status:', exam.value.status)
  console.log('[DEBUG] exam.id:', exam.value.id)
  
  if (!canEdit.value) {
    ElMessage.warning('只有草稿状态的考试才能添加题目')
    return
  }
  
  editingQuestion.value = null
  showFormDialog.value = true
  console.log('[DEBUG] showFormDialog set to:', showFormDialog.value)
  ElMessage.success('打开添加题目对话框')
}

function handleQuestionEdit(question) {
  editingQuestion.value = question
  showFormDialog.value = true
}

function handleFormSuccess() {
  loadDetail()
}

function handleQuestionDelete() {
  loadDetail()
}

function goBack() {
  router.push('/admin/exams')
}

onMounted(loadDetail)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-left .title {
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 12px;
}
</style>
