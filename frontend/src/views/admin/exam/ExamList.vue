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
        <el-table-column label="操作" width="260" fixed="right">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
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

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除考试「${row.title}」吗？此操作不可恢复。`, '删除确认', {
      type: 'error',
    })
    await examApi.deleteExam(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    /* cancelled */
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
