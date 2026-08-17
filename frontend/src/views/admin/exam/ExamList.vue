<template>
  <div class="exam-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">考试列表</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索考试名称"
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
              <el-option label="草稿" value="draft" />
              <el-option label="已发布" value="published" />
              <el-option label="已关闭" value="closed" />
            </el-select>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button type="primary" @click="goCreate">
              <el-icon><Plus /></el-icon>
              新建考试
            </el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="examList" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="考试名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="exam_code" label="考试编码" width="140" />
        <el-table-column prop="position" label="岗位" width="140">
          <template #default="{ row }">
            {{ row.position || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_minutes" label="时长(分)" width="100" />
        <el-table-column prop="question_count" label="题目数" width="90" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="380" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goDetail(row.id)">查看</el-button>
            <el-button
              v-if="row.status === 'draft'"
              size="small"
              type="primary"
              link
              @click="goEdit(row.id)"
            >编辑</el-button>
            <el-button
              size="small"
              type="info"
              link
              @click="handleClone(row)"
            >复制</el-button>
            <el-button
              v-if="row.status === 'draft'"
              size="small"
              type="success"
              link
              @click="handlePublish(row)"
            >发布</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="warning"
              link
              @click="handleClose(row)"
            >关闭</el-button>
            <el-button
              v-if="row.status === 'closed'"
              size="small"
              type="success"
              link
              @click="handleRepublish(row)"
            >再次发布</el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'closed'"
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
      v-model="cloneDialogVisible"
      title="复制试卷"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form :model="{ title: cloneNewTitle }" label-width="100px">
        <el-form-item label="原试卷">
          <span>{{ cloneTargetExam?.title }}</span>
        </el-form-item>
        <el-form-item label="新名称" required>
          <el-input v-model="cloneNewTitle" placeholder="请输入新试卷名称" />
        </el-form-item>
        <el-form-item>
          <span style="color: #909399; font-size: 12px">
            新试卷将复制所有题目（不包含考试记录和答题数据），状态为草稿
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cloneDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmClone">确认复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, CopyDocument } from '@element-plus/icons-vue'
import { examApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const examList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')

const statusText = (s) => ({ draft: '草稿', published: '已发布', closed: '已关闭' }[s] || s)
const statusTagType = (s) => ({ draft: 'info', published: 'success', closed: 'danger' }[s] || 'info')

const cloneDialogVisible = ref(false)
const cloneTargetExam = ref(null)
const cloneNewTitle = ref('')

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) params.keyword = searchQuery.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await examApi.getExamList(params)
    examList.value = res.data.items
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
  router.push('/admin/exams/create')
}

function goDetail(id) {
  router.push(`/admin/exams/${id}`)
}

function goEdit(id) {
  router.push(`/admin/exams/${id}/edit`)
}

async function handlePublish(row) {
  try {
    await ElMessageBox.confirm(`确定发布考试「${row.title}」吗？发布后将不可修改。`, '发布确认', {
      type: 'warning',
    })
    await examApi.publishExam(row.id)
    ElMessage.success('发布成功')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

async function handleClose(row) {
  try {
    await ElMessageBox.confirm(`确定关闭考试「${row.title}」吗？`, '关闭确认', { type: 'warning' })
    await examApi.closeExam(row.id)
    ElMessage.success('已关闭')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

async function handleRepublish(row) {
  try {
    await ElMessageBox.confirm(
      `确定重新发布考试「${row.title}」吗？重新发布后将保留原有题目和历史成绩。`,
      '重新发布确认',
      { type: 'warning' }
    )
    await examApi.publishExam(row.id)
    ElMessage.success('重新发布成功')
    fetchList()
  } catch (e) {
    /* cancelled */
  }
}

function handleClone(row) {
  cloneTargetExam.value = row
  cloneNewTitle.value = `${row.title}（副本）`
  cloneDialogVisible.value = true
}

async function confirmClone() {
  if (!cloneNewTitle.value.trim()) {
    ElMessage.warning('请输入新试卷名称')
    return
  }
  try {
    await examApi.cloneExam(cloneTargetExam.value.id, cloneNewTitle.value.trim())
    ElMessage.success('复制成功')
    cloneDialogVisible.value = false
    fetchList()
  } catch (e) {
    /* error handled by interceptor */
  }
}

async function handleDelete(row) {
  try {
    // 根据状态设置不同的确认提示
    let confirmMsg = `确定删除考试「${row.title}」吗？此操作不可恢复。`
    if (row.status === 'closed') {
      confirmMsg = `该试卷已结束考试，确认删除？\n\n试卷名称：${row.title}\n此操作可能影响历史成绩查看，请谨慎操作。`
    }
    
    await ElMessageBox.confirm(confirmMsg, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    })
    await examApi.deleteExam(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    /* cancelled or error */
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
