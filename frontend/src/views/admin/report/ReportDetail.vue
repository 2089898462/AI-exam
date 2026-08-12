<template>
  <div class="report-detail-container">
    <el-card v-loading="loading">
      <template v-if="report">
        <!-- 头部信息 -->
        <div class="header-section">
          <el-page-header @back="goBack" :content="`返回报告列表`" />
        </div>

        <el-descriptions :column="3" border style="margin-top: 20px">
          <el-descriptions-item label="候选人">{{ report.candidate_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="考试名称">{{ report.exam_title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatTime(report.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="总分">
            <span class="score">{{ report.total_score ?? '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="客观题得分">{{ report.auto_score ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="AI评分得分">{{ report.ai_score ?? '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 总体评价 -->
        <el-divider content-position="left">总体评价</el-divider>
        <div class="summary-section">
          <el-tag 
            :type="getRecommendationType(report.recommendation)" 
            size="large"
            effect="dark"
          >
            {{ report.recommendation }}
          </el-tag>
          <p class="summary-text">{{ report.summary || '暂无总结' }}</p>
        </div>

        <!-- 优势与薄弱 -->
        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <el-icon style="color: #67c23a"><Medal /></el-icon>
                  <span>优势能力</span>
                </div>
              </template>
              <el-timeline v-if="report.strengths && report.strengths.length">
                <el-timeline-item 
                  v-for="(item, index) in report.strengths" 
                  :key="index"
                  type="success"
                >
                  {{ item }}
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <el-icon style="color: #e6a23c"><Warning /></el-icon>
                  <span>薄弱环节</span>
                </div>
              </template>
              <el-timeline v-if="report.weaknesses && report.weaknesses.length">
                <el-timeline-item 
                  v-for="(item, index) in report.weaknesses" 
                  :key="index"
                  type="warning"
                >
                  {{ item }}
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 能力维度分析 -->
        <el-divider content-position="left">能力维度分析</el-divider>
        <div v-if="report.skill_analysis && Object.keys(report.skill_analysis).length" class="skill-analysis">
          <el-tag 
            v-for="(value, key) in report.skill_analysis" 
            :key="key"
            class="skill-tag"
            effect="plain"
          >
            <strong>{{ key }}：</strong>{{ value }}
          </el-tag>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />

        <!-- 面试建议 -->
        <el-divider content-position="left">面试建议</el-divider>
        <el-card shadow="never" v-if="report.interview_suggestions && report.interview_suggestions.length">
          <ol class="suggestion-list">
            <li v-for="(item, index) in report.interview_suggestions" :key="index">
              {{ item }}
            </li>
          </ol>
        </el-card>
        <el-empty v-else description="暂无数据" :image-size="60" />

        <!-- 技术信息 -->
        <el-divider content-position="left">技术信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="使用模型">{{ report.model_used }}</el-descriptions-item>
          <el-descriptions-item label="Prompt版本">{{ report.prompt_version }}</el-descriptions-item>
        </el-descriptions>
      </template>

      <el-empty v-else-if="!loading" description="报告不存在或已被删除" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Medal, Warning } from '@element-plus/icons-vue'
import { reportApi } from '@/api/report'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const report = ref(null)

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

const goBack = () => {
  router.back()
}

const loadReport = async () => {
  const reportId = route.params.id
  if (!reportId) {
    ElMessage.error('报告ID不存在')
    return
  }

  loading.value = true
  try {
    const res = await reportApi.getDetail(reportId)
    report.value = res.data
  } catch (err) {
    ElMessage.error('加载报告详情失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report-detail-container {
  padding: 20px;
}

.header-section {
  margin-bottom: 10px;
}

.summary-section {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.summary-text {
  font-size: 16px;
  line-height: 1.6;
  color: #606266;
  margin: 0;
}

.score {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.skill-analysis {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.skill-tag {
  font-size: 13px;
  line-height: 1.5;
  padding: 8px 12px;
}

.suggestion-list {
  padding-left: 20px;
  line-height: 2;
}

.suggestion-list li {
  margin-bottom: 8px;
}
</style>
