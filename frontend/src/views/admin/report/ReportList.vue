<template>
  <div class="report-list-container">
    <el-card>
      <div class="header">
        <h2>AI 分析报告</h2>
        <div class="filters">
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
            <el-option label="已完成" value="completed" />
            <el-option label="待处理" value="pending" />
          </el-select>
          <el-button type="primary" @click="loadReports">查询</el-button>
        </div>
      </div>

      <el-table :data="reports" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="exam_title" label="考试名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="candidate_name" label="候选人" width="120" />
        <el-table-column prop="recommendation" label="推荐等级" width="120">
          <template #default="{ row }">
            <el-tag :type="getRecommendationType(row.recommendation)">
              {{ row.recommendation }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">
              {{ row.status === 'completed' ? '已完成' : '生成中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">查看详情</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadReports"
          @current-change="loadReports"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reportApi } from '@/api/report'

const router = useRouter()

const loading = ref(false)
const reports = ref([])

const filters = reactive({
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const getRecommendationType = (rec) => {
  const map = {
    '强烈推荐': 'success',
    '推荐': '',
    '保留考虑': 'warning',
    '不推荐': 'danger',
  }
  return map[rec] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const loadReports = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.status) {
      params.status = filters.status
    }
    const res = await reportApi.getList(params)
    reports.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err) {
    ElMessage.error('加载报告列表失败')
  } finally {
    loading.value = false
  }
}

const viewDetail = (row) => {
  router.push(`/admin/reports/${row.id}`)
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除候选人 "${row.candidate_name}" 的报告吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await reportApi.delete(row.id)
    ElMessage.success('删除成功')
    loadReports()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-list-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
}

.filters {
  display: flex;
  gap: 10px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
