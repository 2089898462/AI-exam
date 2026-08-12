<template>
  <div class="exam-participants">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="title">考试参与人员管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              添加人员
            </el-button>
            <el-button @click="showBatchDialog = true">
              <el-icon><Files /></el-icon>
              批量添加
            </el-button>
            <el-button @click="handleSync" :disabled="!examId">
              <el-icon><Refresh /></el-icon>
              同步状态
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计信息 -->
      <el-descriptions :column="5" border class="stats" v-if="countData">
        <el-descriptions-item label="总人数">
          {{ countData.total }}
        </el-descriptions-item>
        <el-descriptions-item label="已分配">
          <el-tag size="small" type="info">{{ countData.assigned }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="未开始">
          <el-tag size="small" type="warning">{{ countData.not_started }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进行中">
          <el-tag size="small" type="primary">{{ countData.in_progress }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="已完成">
          <el-tag size="small" type="success">{{ countData.completed }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <!-- 搜索筛选 -->
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索姓名/手机/邮箱"
          clearable
          style="width: 240px; margin-right: 12px"
          @keyup.enter="fetchList"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 140px; margin-right: 12px"
        >
          <el-option label="已分配" value="assigned" />
          <el-option label="未开始" value="not_started" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已提交" value="submitted" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-button type="primary" @click="fetchList">搜索</el-button>
      </div>

      <!-- 人员列表 -->
      <el-table :data="participantList" border stripe style="margin-top: 16px">
        <el-table-column label="#" type="index" width="60" />
        <el-table-column prop="candidate_name" label="姓名" width="120" />
        <el-table-column prop="candidate_phone" label="手机号" width="140">
          <template #default="{ row }">
            {{ row.candidate_phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="candidate_email" label="邮箱" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.candidate_email || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="考试进度" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.completed" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.exam_record_status === 'in_progress'" type="warning" size="small">进行中</el-tag>
            <el-tag v-else-if="row.exam_record_status === 'submitted'" type="primary" size="small">已提交</el-tag>
            <el-tag v-else type="info" size="small">未开始</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              link
              @click="handleRemove(row)"
              :disabled="row.completed || row.exam_record_status"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && participantList.length === 0" description="暂无参与人员" />

      <el-pagination
        v-if="total > 0"
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

    <!-- 添加人员对话框 -->
    <el-dialog v-model="showDialog" title="添加考试人员" width="480px">
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="候选人姓名" prop="candidate_name">
          <el-input v-model="formData.candidate_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="candidate_phone">
          <el-input v-model="formData.candidate_phone" placeholder="选填，用于唯一标识" />
        </el-form-item>
        <el-form-item label="邮箱" prop="candidate_email">
          <el-input v-model="formData.candidate_email" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定添加</el-button>
      </template>
    </el-dialog>

    <!-- 批量添加对话框 -->
    <el-dialog v-model="showBatchDialog" title="批量添加考试人员" width="600px">
      <div class="batch-tips">
        <p>每行一个人员，格式：姓名,手机号,邮箱（逗号分隔，手机号和邮箱可选）</p>
        <p>示例：</p>
        <p><code>张三,13800138000,zhangsan@example.com</code></p>
        <p><code>李四,13900139000</code></p>
        <p><code>王五</code></p>
      </div>
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="8"
        placeholder="请输入人员信息"
      />
      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" @click="handleBatchAdd">确定添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Files, Refresh, Search } from '@element-plus/icons-vue'
import { participantApi } from '@/api'

const props = defineProps({
  examId: {
    type: Number,
    required: true,
  },
})

const loading = ref(false)
const participantList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')
const countData = ref(null)

const showDialog = ref(false)
const showBatchDialog = ref(false)
const formRef = ref(null)
const batchText = ref('')

const formData = ref({
  candidate_name: '',
  candidate_phone: '',
  candidate_email: '',
})

const formRules = {
  candidate_name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 1, max: 64, message: '姓名长度 1-64 个字符', trigger: 'blur' },
  ],
}

const statusText = (s) => ({
  assigned: '已分配',
  not_started: '未开始',
  in_progress: '进行中',
  submitted: '已提交',
  completed: '已完成',
}[s] || s)

const statusTagType = (s) => ({
  assigned: 'info',
  not_started: 'warning',
  in_progress: 'primary',
  submitted: 'success',
  completed: 'success',
}[s] || 'info')

async function fetchList() {
  if (!props.examId) return
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) params.keyword = searchQuery.value
    if (statusFilter.value) params.status = statusFilter.value

    const res = await participantApi.getParticipants(props.examId, params)
    participantList.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchCount() {
  if (!props.examId) return
  try {
    const res = await participantApi.getParticipantCount(props.examId)
    countData.value = res.data
  } catch (e) {
    console.error(e)
  }
}

function showAddDialog() {
  formData.value = {
    candidate_name: '',
    candidate_phone: '',
    candidate_email: '',
  }
  showDialog.value = true
}

async function handleAdd() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  try {
    await participantApi.addParticipant(props.examId, formData.value)
    ElMessage.success('添加成功')
    showDialog.value = false
    fetchList()
    fetchCount()
  } catch (e) {
    console.error(e)
  }
}

async function handleBatchAdd() {
  if (!batchText.value.trim()) {
    ElMessage.warning('请输入人员信息')
    return
  }

  const lines = batchText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line)

  const participants = lines.map((line) => {
    const parts = line.split(',').map((p) => p.trim())
    return {
      candidate_name: parts[0] || '',
      candidate_phone: parts[1] || null,
      candidate_email: parts[2] || null,
    }
  }).filter((p) => p.candidate_name)

  if (participants.length === 0) {
    ElMessage.warning('无有效人员数据')
    return
  }

  try {
    const res = await participantApi.addParticipantsBatch(props.examId, participants)
    const { success_count, errors, total } = res.data
    if (errors && errors.length > 0) {
      ElMessage.warning(`成功 ${success_count} 人，失败 ${errors.length} 人：${errors.join('；')}`)
    } else {
      ElMessage.success(`成功添加 ${success_count} 人`)
    }
    showBatchDialog.value = false
    batchText.value = ''
    fetchList()
    fetchCount()
  } catch (e) {
    console.error(e)
  }
}

async function handleRemove(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除参与人员「${row.candidate_name}」吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await participantApi.removeParticipant(row.id)
    ElMessage.success('删除成功')
    fetchList()
    fetchCount()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}

async function handleSync() {
  try {
    const res = await participantApi.syncParticipantStatus(props.examId)
    ElMessage.success(`同步完成，更新 ${res.data.updated_count} 条记录`)
    fetchList()
    fetchCount()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchList()
  fetchCount()
})

watch(
  () => props.examId,
  () => {
    if (props.examId) {
      fetchList()
      fetchCount()
    }
  }
)
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
  gap: 8px;
}

.stats {
  background: #f5f7fa;
}

.filter-bar {
  display: flex;
  align-items: center;
}

.batch-tips {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
}

.batch-tips p {
  margin: 4px 0;
}

.batch-tips code {
  background: #e6e8eb;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}
</style>
