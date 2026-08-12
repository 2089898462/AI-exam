<template>
  <div class="template-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">试卷模板列表</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索模板名称"
              clearable
              style="width: 240px; margin-right: 12px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select
              v-model="statusFilter"
              placeholder="状态"
              clearable
              style="width: 120px; margin-right: 12px"
            >
              <el-option label="启用" value="active" />
              <el-option label="停用" value="inactive" />
            </el-select>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button type="primary" @click="goCreate">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="templateList" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="模板名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="question_count" label="题目数" width="90" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goDetail(row.id)">查看</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small"
              type="primary"
              link
              @click="goEdit(row.id)"
            >编辑</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small"
              type="success"
              link
              @click="handleCreateExam(row)"
            >创建考试</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small"
              type="warning"
              link
              @click="handleDeactivate(row)"
            >停用</el-button>
            <el-button
              v-if="row.status === 'inactive'"
              size="small"
              type="success"
              link
              @click="handleActivate(row)"
            >启用</el-button>
            <el-button
              size="small"
              type="danger"
              link
              @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @size-change="fetchList"
        @current-change="fetchList"
      />
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { templateApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const templateList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')

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
const currentTemplateId = ref(null)

const statusText = (s) => ({ active: '启用', inactive: '停用' }[s] || s)

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) params.keyword = searchQuery.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await templateApi.getTemplateList(params)
    templateList.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchList()
}

function goCreate() {
  router.push('/admin/templates/create')
}

function goDetail(id) {
  router.push(`/admin/templates/${id}`)
}

function goEdit(id) {
  router.push(`/admin/templates/${id}/edit`)
}

async function handleActivate(row) {
  try {
    await ElMessageBox.confirm(`确定启用模板「${row.name}」吗？`, '启用确认')
    await templateApi.activateTemplate(row.id)
    ElMessage.success('启用成功')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

async function handleDeactivate(row) {
  try {
    await ElMessageBox.confirm(`确定停用模板「${row.name}」吗？`, '停用确认', { type: 'warning' })
    await templateApi.deactivateTemplate(row.id)
    ElMessage.success('停用成功')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${row.name}」吗？此操作不可恢复。`, '删除确认', {
      type: 'error',
    })
    await templateApi.deleteTemplate(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

function handleCreateExam(row) {
  currentTemplateId.value = row.id
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
    
    const res = await templateApi.createExamFromTemplate(currentTemplateId.value, data)
    ElMessage.success('考试创建成功')
    createExamDialogVisible.value = false
    
    if (res.data && res.data.exam_id) {
      router.push(`/admin/exams/${res.data.exam_id}`)
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchList)
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

.header-actions {
  display: flex;
  align-items: center;
}
</style>
