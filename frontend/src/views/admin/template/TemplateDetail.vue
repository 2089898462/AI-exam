<template>
  <div class="template-detail">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="title">模板详情</span>
          <div>
            <el-button @click="goBack">
              <el-icon><ArrowLeft /></el-icon>
              返回列表
            </el-button>
            <el-button type="primary" @click="goEdit">
              <el-icon><Edit /></el-icon>
              编辑模板
            </el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="模板ID">
          {{ templateData.id }}
        </el-descriptions-item>
        <el-descriptions-item label="模板名称">
          {{ templateData.name }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="templateData.status === 'active' ? 'success' : 'info'">
            {{ templateData.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="题目数量">
          {{ templateData.question_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ templateData.created_at }}
        </el-descriptions-item>
        <el-descriptions-item label="模板描述" :span="2" v-if="templateData.description">
          {{ templateData.description }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">题目列表</el-divider>

      <el-table :data="templateData.questions || []" border v-if="templateData.questions && templateData.questions.length > 0">
        <el-table-column label="#" type="index" width="60" />
        <el-table-column label="题型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ questionTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="question_no" label="编号" width="80" />
        <el-table-column prop="content" label="题目内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="score" label="分值" width="80" />
        <el-table-column label="答案" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatAnswer(row) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="模板中暂无题目" />

      <el-divider content-position="left">快速操作</el-divider>
      <div class="action-buttons">
        <el-button type="primary" size="large" @click="handleCreateExam">
          <el-icon><DocumentAdd /></el-icon>
          基于此模板创建考试
        </el-button>
      </div>
    </el-card>

    <el-dialog
      v-model="createExamDialogVisible"
      title="基于模板创建考试"
      width="500px"
    >
      <el-form :model="createExamForm" :rules="createExamRules" ref="createExamFormRef" label-width="120px">
        <el-form-item label="考试标题" prop="title">
          <el-input v-model="createExamForm.title" placeholder="留空自动生成" />
        </el-form-item>
        <el-form-item label="考试编码" prop="exam_code">
          <el-input v-model="createExamForm.exam_code" placeholder="可选" />
        </el-form-item>
        <el-form-item label="岗位" prop="position">
          <el-input v-model="createExamForm.position" placeholder="可选" />
        </el-form-item>
        <el-form-item label="考试时长(分)" prop="duration_minutes">
          <el-input-number v-model="createExamForm.duration_minutes" :min="1" :max="1440" />
        </el-form-item>
        <el-form-item label="及格分数" prop="pass_score">
          <el-input-number v-model="createExamForm.pass_score" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createExamDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateExam">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, DocumentAdd } from '@element-plus/icons-vue'
import { templateApi } from '@/api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const templateData = ref({})

const createExamDialogVisible = ref(false)
const createExamForm = ref({
  title: '',
  exam_code: '',
  position: '',
  duration_minutes: 60,
  pass_score: 60,
})
const createExamFormRef = ref(null)
const createExamRules = {}

const questionTypeText = (type) => ({
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '简答题',
})[type] || type

function formatAnswer(row) {
  if (row.type === 'true_false') {
    return row.answer === 'true' ? '正确 ✓' : '错误 ✗'
  }
  return row.answer
}

async function loadTemplate() {
  loading.value = true
  try {
    const res = await templateApi.getTemplateDetail(route.params.id)
    templateData.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/admin/templates')
}

function goEdit() {
  router.push(`/admin/templates/${route.params.id}/edit`)
}

function handleCreateExam() {
  createExamForm.value = {
    title: '',
    exam_code: '',
    position: '',
    duration_minutes: 60,
    pass_score: 60,
  }
  createExamDialogVisible.value = true
}

async function confirmCreateExam() {
  if (createExamFormRef.value) {
    try {
      await createExamFormRef.value.validate()
    } catch {
      return
    }
  }
  
  try {
    const data = { ...createExamForm.value }
    if (!data.title) delete data.title
    if (!data.exam_code) delete data.exam_code
    if (!data.position) delete data.position
    
    const res = await templateApi.createExamFromTemplate(route.params.id, data)
    ElMessage.success('考试创建成功')
    createExamDialogVisible.value = false
    
    if (res.data && res.data.exam_id) {
      router.push(`/admin/exams/${res.data.exam_id}`)
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadTemplate)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  font-size: 16px;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 12px;
}
</style>
