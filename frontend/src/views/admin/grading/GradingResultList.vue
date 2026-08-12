<template>
  <div class="grading-result-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">评分结果</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索候选人姓名/手机/邮箱"
              clearable
              style="width: 240px; margin-right: 12px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select
              v-model="statusFilter"
              placeholder="评分状态"
              clearable
              style="width: 140px; margin-right: 12px"
            >
              <el-option label="待评分" value="pending" />
              <el-option label="评分中" value="grading" />
              <el-option label="已完成" value="completed" />
              <el-option label="评分失败" value="failed" />
            </el-select>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="margin-right: 12px"
            />
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="resultList" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="exam_record_id" label="考试记录ID" width="100" />
        <el-table-column prop="candidate_name" label="候选人" width="120" />
        <el-table-column prop="candidate_phone" label="手机" width="130">
          <template #default="{ row }">
            {{ row.candidate_phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="评分类型" width="100">
          <template #default="{ row }">
            <el-tag :type="gradingTypeTag(row.grading_type)" size="small">
              {{ gradingTypeText(row.grading_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_score" label="总分" width="100">
          <template #default="{ row }">
            <span :class="{ 'text-success': row.passed, 'text-danger': row.passed === false }">
              {{ row.total_score ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="及格状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.passed !== null && row.passed !== undefined" :type="row.passed ? 'success' : 'danger'">
              {{ row.passed ? '及格' : '不及格' }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goDetail(row.exam_record_id)">
              查看详情
            </el-button>
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
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { gradingResultApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const resultList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])

const statusText = (s) => ({ pending: '待评分', grading: '评分中', completed: '已完成', failed: '评分失败' }[s] || s)
const statusTagType = (s) => ({ pending: 'info', grading: 'warning', completed: 'success', failed: 'danger' }[s] || 'info')
const gradingTypeText = (t) => ({ auto: '自动', ai: 'AI', hybrid: '混合' }[t] || t)
const gradingTypeTag = (t) => ({ auto: '', ai: 'warning', hybrid: 'info' }[t] || '')

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) params.keyword = searchQuery.value
    if (statusFilter.value) params.status = statusFilter.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString().split('T')[0]
      params.end_date = dateRange.value[1].toISOString().split('T')[0]
    }
    const res = await gradingResultApi.getResults(params)
    resultList.value = res.data.items
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

function goDetail(examRecordId) {
  router.push(`/admin/grading/${examRecordId}`)
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

.text-success {
  color: #67c23a;
  font-weight: 600;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}
</style>
