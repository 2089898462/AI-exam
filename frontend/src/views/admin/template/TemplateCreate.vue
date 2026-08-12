<template>
  <div class="template-create">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="title">{{ isEdit ? '编辑模板' : '创建模板' }}</span>
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

        <el-form-item label="模板名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模板名称" maxlength="200" show-word-limit />
        </el-form-item>

        <el-form-item label="模板描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述（选填）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-divider content-position="left">题目管理</el-divider>

        <div class="section-actions">
          <el-button type="primary" :disabled="!isEdit" @click="showAddQuestionDialog">
            <el-icon><Plus /></el-icon>
            添加题目
          </el-button>
          <el-button type="danger" :disabled="!isEdit || questionList.length === 0" @click="clearAllQuestions">
            清空所有题目
          </el-button>
          <span class="tip" v-if="!isEdit">保存模板后可添加题目</span>
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
          <el-table-column label="操作" width="150">
            <template #default="{ $index, row }">
              <el-button size="small" type="primary" link @click="editQuestion(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click="removeQuestion($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无题目，请添加题目" />
      </el-form>

      <div class="form-actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">保存</el-button>
      </div>
    </el-card>

    <el-dialog
      v-model="questionDialogVisible"
      :title="editingQuestionId ? '编辑题目' : '添加题目'"
      width="600px"
    >
      <el-form :model="questionForm" :rules="questionRules" ref="questionFormRef" label-width="100px">
        <el-form-item label="题型" prop="type">
          <el-select v-model="questionForm.type" placeholder="请选择题型">
            <el-option label="单选题" value="single_choice" />
            <el-option label="多选题" value="multiple_choice" />
            <el-option label="判断题" value="true_false" />
            <el-option label="简答题" value="short_answer" />
          </el-select>
        </el-form-item>
        <el-form-item label="题目编号" prop="question_no">
          <el-input v-model="questionForm.question_no" placeholder="选填" />
        </el-form-item>
        <el-form-item label="题目分类" prop="category">
          <el-input v-model="questionForm.category" placeholder="选填" />
        </el-form-item>
        <el-form-item label="题目内容" prop="content">
          <el-input v-model="questionForm.content" type="textarea" :rows="2" placeholder="请输入题目内容" />
        </el-form-item>
        <el-form-item label="选项" prop="options" v-if="questionForm.type === 'single_choice' || questionForm.type === 'multiple_choice'">
          <div class="options-editor">
            <div v-for="(opt, idx) in questionForm.options" :key="idx" class="option-item">
              <span class="option-label">{{ String.fromCharCode(65 + idx) }}.</span>
              <el-input v-model="opt.text" placeholder="选项内容" />
              <el-button size="small" type="danger" link @click="removeOption(idx)" :disabled="questionForm.options.length <= 2">删除</el-button>
            </div>
            <el-button type="primary" link @click="addOption" :disabled="questionForm.options.length >= 10">添加选项</el-button>
          </div>
        </el-form-item>
        <el-form-item label="答案" prop="answer">
          <el-input 
            v-if="questionForm.type === 'true_false'" 
            v-model="questionForm.answer" 
            placeholder="true 或 false"
          />
          <el-input 
            v-else-if="questionForm.type === 'single_choice' || questionForm.type === 'multiple_choice'"
            v-model="questionForm.answer" 
            placeholder="如 A 或 A,B,C"
          />
          <el-input 
            v-else 
            v-model="questionForm.answer" 
            type="textarea" 
            :rows="3"
            placeholder="请输入参考答案"
          />
        </el-form-item>
        <el-form-item label="分值" prop="score">
          <el-input-number v-model="questionForm.score" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="questionForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveQuestion">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { templateApi } from '@/api'

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const questionList = ref([])

const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '',
  description: '',
})

const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
}

const questionTypeText = (type) => ({
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '简答题',
})[type] || type

// 题目对话框相关
const questionDialogVisible = ref(false)
const editingQuestionId = ref(null)
const questionFormRef = ref(null)
const questionForm = ref({
  type: 'single_choice',
  question_no: '',
  category: '',
  content: '',
  options: [{ label: 'A', text: '' }, { label: 'B', text: '' }],
  answer: '',
  score: 0,
  sort_order: 0,
})

const questionRules = {
  type: [{ required: true, message: '请选择题型', trigger: 'change' }],
  content: [{ required: true, message: '请输入题目内容', trigger: 'blur' }],
  answer: [{ required: true, message: '请输入答案', trigger: 'blur' }],
}

watch(() => questionForm.value.type, (newType) => {
  if (newType === 'single_choice' || newType === 'multiple_choice') {
    if (!questionForm.value.options || questionForm.value.options.length < 2) {
      questionForm.value.options = [{ label: 'A', text: '' }, { label: 'B', text: '' }]
    }
    questionForm.value.answer = ''
  } else if (newType === 'true_false') {
    questionForm.value.options = []
    questionForm.value.answer = 'true'
  } else {
    questionForm.value.options = []
    questionForm.value.answer = ''
  }
})

async function loadTemplate() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const res = await templateApi.getTemplateDetail(route.params.id)
    const data = res.data
    form.value = {
      name: data.name,
      description: data.description || '',
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
      await templateApi.updateTemplate(route.params.id, form.value)
      ElMessage.success('保存成功')
      router.push(`/admin/templates/${route.params.id}`)
    } else {
      const res = await templateApi.createTemplate(form.value)
      ElMessage.success('创建成功')
      router.push(`/admin/templates/${res.data.id}`)
    }
  } catch (e) {
    /* handled by interceptor */
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.push('/admin/templates')
}

function showAddQuestionDialog() {
  editingQuestionId.value = null
  questionForm.value = {
    type: 'single_choice',
    question_no: '',
    category: '',
    content: '',
    options: [{ label: 'A', text: '' }, { label: 'B', text: '' }],
    answer: '',
    score: 0,
    sort_order: questionList.value.length + 1,
  }
  questionDialogVisible.value = true
}

function editQuestion(row) {
  editingQuestionId.value = row.id
  questionForm.value = {
    type: row.type,
    question_no: row.question_no || '',
    category: row.category || '',
    content: row.content,
    options: row.options || [{ label: 'A', text: '' }, { label: 'B', text: '' }],
    answer: row.answer,
    score: row.score,
    sort_order: row.sort_order || 0,
  }
  questionDialogVisible.value = true
}

function removeQuestion(index) {
  const question = questionList.value[index]
  if (confirm('确定删除此题吗？')) {
    if (question.id) {
      templateApi.deleteTemplateQuestion(route.params.id, question.id).then(() => {
        ElMessage.success('删除成功')
        questionList.value.splice(index, 1)
      })
    } else {
      questionList.value.splice(index, 1)
    }
  }
}

function clearAllQuestions() {
  if (confirm('确定清空所有题目吗？此操作不可恢复。')) {
    templateApi.deleteAllTemplateQuestions(route.params.id).then(() => {
      ElMessage.success('清空成功')
      questionList.value = []
    })
  }
}

function addOption() {
  const len = questionForm.value.options.length
  questionForm.value.options.push({ label: String.fromCharCode(65 + len), text: '' })
}

function removeOption(index) {
  questionForm.value.options.splice(index, 1)
  // 重新编号
  questionForm.value.options.forEach((opt, i) => {
    opt.label = String.fromCharCode(65 + i)
  })
}

async function saveQuestion() {
  const valid = await questionFormRef.value.validate().catch(() => false)
  if (!valid) return

  // 验证选项
  if (questionForm.value.type === 'single_choice' || questionForm.value.type === 'multiple_choice') {
    const validOptions = questionForm.value.options.filter(o => o.text && o.text.trim())
    if (validOptions.length < 2) {
      ElMessage.warning('至少需要2个有效选项')
      return
    }
  }

  // 验证答案
  if (questionForm.value.type === 'single_choice') {
    const answer = questionForm.value.answer.toUpperCase()
    const validLabels = questionForm.value.options.map((_, i) => String.fromCharCode(65 + i))
    if (!validLabels.includes(answer)) {
      ElMessage.warning('答案必须是选项中的一个')
      return
    }
    questionForm.value.answer = answer
  } else if (questionForm.value.type === 'multiple_choice') {
    const answers = questionForm.value.answer.toUpperCase().split(',').map(s => s.trim()).filter(Boolean)
    const validLabels = questionForm.value.options.map((_, i) => String.fromCharCode(65 + i))
    for (a in answers) {
      if (!validLabels.includes(a)) {
        ElMessage.warning(`答案 ${a} 无效`)
        return
      }
    }
    questionForm.value.answer = answers.join(',')
  }

  try {
    const data = { ...questionForm.value }
    if (editingQuestionId.value) {
      await templateApi.updateTemplateQuestion(
        route.params.id,
        editingQuestionId.value,
        data
      )
      ElMessage.success('更新成功')
    } else {
      await templateApi.createTemplateQuestion(route.params.id, data)
      ElMessage.success('添加成功')
    }
    questionDialogVisible.value = false
    loadTemplate() // 重新加载模板数据
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

.options-editor {
  width: 100%;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.option-label {
  width: 24px;
  font-weight: 600;
}

.option-item .el-input {
  flex: 1;
}
</style>
