<template>
  <div class="exam-create">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="title">{{ isEdit ? '编辑考试' : '创建考试' }}</span>
          <el-button @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        label-position="right"
      >
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="考试名称" prop="title">
          <el-input v-model="form.title" placeholder="请输入考试名称" maxlength="200" show-word-limit />
        </el-form-item>

        <el-form-item label="考试编码" prop="exam_code">
          <el-input v-model="form.exam_code" placeholder="选填，建议唯一标识" maxlength="50" />
        </el-form-item>

        <el-form-item label="岗位" prop="position">
          <el-input v-model="form.position" placeholder="请输入考试所属岗位" maxlength="100" />
        </el-form-item>

        <el-form-item label="考试说明" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入考试说明（选填）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="考试时长" prop="duration_minutes">
              <el-input-number v-model="form.duration_minutes" :min="1" :max="1440" />
              <span style="margin-left: 8px">分钟</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="及格分数" prop="pass_score">
              <el-input-number v-model="form.pass_score" :min="0" :precision="1" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">题目管理</el-divider>

        <div class="section-actions">
          <el-upload
            :show-file-list="false"
            :before-upload="handleJsonImport"
            accept=".json"
          >
            <el-button type="primary" :disabled="!isEdit">
              <el-icon><Upload /></el-icon>
              导入 JSON
            </el-button>
          </el-upload>
          <el-button type="success" :disabled="!isEdit">
            <el-icon><Plus /></el-icon>
            手动添加题目
          </el-button>
          <span class="tip" v-if="!isEdit">创建考试后可添加题目</span>
        </div>

        <el-table :data="questionList" border style="margin-top: 12px" v-if="questionList.length > 0">
          <el-table-column label="#" type="index" width="60" />
          <el-table-column label="题型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ questionTypeText(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="question_no" label="编号" width="80" />
          <el-table-column prop="content" label="题目内容" min-width="200" show-overflow-tooltip />
          <el-table-column prop="score" label="分值" width="80" />
          <el-table-column label="操作" width="100">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="removeQuestion($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无题目，请导入 JSON 或手动添加" />
      </el-form>

      <div class="form-actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Upload, Plus } from '@element-plus/icons-vue'
import { examApi } from '@/api'

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const questionList = ref([])

const isEdit = computed(() => !!route.params.id)

const form = ref({
  title: '',
  exam_code: '',
  position: '',
  description: '',
  duration_minutes: 60,
  pass_score: 60,
})

const rules = {
  title: [{ required: true, message: '请输入考试名称', trigger: 'blur' }],
  duration_minutes: [{ required: true, message: '请设置考试时长', trigger: 'blur' }],
}

const questionTypeText = (type) => ({
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '问答题',
})[type] || type

async function loadExam() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const res = await examApi.getExamDetail(route.params.id)
    const data = res.data
    form.value = {
      title: data.title,
      exam_code: data.exam_code || '',
      position: data.position || '',
      description: data.description || '',
      duration_minutes: data.duration_minutes,
      pass_score: data.pass_score,
    }
    questionList.value = data.questions || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await examApi.updateExam(route.params.id, form.value)
      ElMessage.success('保存成功')
      router.push(`/admin/exams/${route.params.id}`)
    } else {
      const res = await examApi.createExam(form.value)
      ElMessage.success('创建成功')
      router.push('/admin/exams')
    }
  } catch (e) {
    /* handled by interceptor */
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.push('/admin/exams')
}

function handleJsonImport(file) {
  if (!file) return
  if (!file.name.endsWith('.json')) {
    ElMessage.error('仅支持 .json 格式文件')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('文件大小超过限制，最大支持 5MB')
    return false
  }

  if (!route.params.id) {
    ElMessage.warning('请先保存考试后再导入题目')
    return false
  }

  const examId = route.params.id
  examApi.importExam(examId, file)
    .then(res => {
      ElMessage.success(`导入成功，共导入 ${res.data.imported_count} 道题目`)
      loadExam()
    })
    .catch(err => {
      const msg = err?.message || '导入失败'
      ElMessage.error(msg)
    })

  return false
}

function removeQuestion(index) {
  questionList.value.splice(index, 1)
}

onMounted(loadExam)
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

.section-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.section-actions .tip {
  color: #909399;
  font-size: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
