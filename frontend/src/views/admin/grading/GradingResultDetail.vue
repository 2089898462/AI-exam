<template>
  <div class="grading-result-detail">
    <el-page-header @back="goBack" content="返回列表" style="margin-bottom: 16px" />

    <template v-if="loading">
      <el-card v-loading="true">
        <div style="height: 300px"></div>
      </el-card>
    </template>

    <template v-else-if="detail">
      <!-- 基本信息卡片 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
          <el-card>
            <template #header>
              <span class="card-title">候选人信息</span>
            </template>
            <el-descriptions :column="isMobile ? 1 : 2" border>
              <el-descriptions-item label="候选人">{{ detail.candidate_name }}</el-descriptions-item>
              <el-descriptions-item label="手机">{{ detail.candidate_phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="邮箱" :span="isMobile ? 1 : 2">{{ detail.candidate_email || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
          <el-card>
            <template #header>
              <span class="card-title">考试信息</span>
            </template>
            <el-descriptions :column="isMobile ? 1 : 2" border>
              <el-descriptions-item label="考试">{{ detail.exam_title }}</el-descriptions-item>
              <el-descriptions-item label="考试ID">{{ detail.exam_id }}</el-descriptions-item>
              <el-descriptions-item label="考试记录ID" :span="isMobile ? 1 : 2">{{ detail.exam_record_id }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <!-- S8.4.3-b: 监考风险摘要卡片 -->
      <el-card v-if="monitorData.has_monitor_data" class="risk-summary-card" style="margin-bottom: 16px">
        <template #header>
          <div class="card-header-with-toggle">
            <span class="card-title">监考风险摘要</span>
            <el-tag :type="riskLevelTagType(monitorData.risk_level)" effect="dark" size="large">
              {{ riskLevelText(monitorData.risk_level) }}
            </el-tag>
          </div>
        </template>
        
        <!-- 风险描述区 -->
        <div class="risk-summary-content" :class="'risk-' + monitorData.risk_level">
          <!-- normal: 正常 -->
          <template v-if="monitorData.risk_level === 'normal'">
            <el-icon class="risk-icon success"><CircleCheckFilled /></el-icon>
            <div class="risk-text">
              <div class="risk-title">监考正常</div>
              <div class="risk-desc">考试期间未检测到明显异常行为</div>
            </div>
          </template>
          
          <!-- low: 低风险 -->
          <template v-else-if="monitorData.risk_level === 'low'">
            <el-icon class="risk-icon warning"><WarningFilled /></el-icon>
            <div class="risk-text">
              <div class="risk-title">存在轻微异常行为</div>
              <div class="risk-desc">
                离开{{ monitorData.leave_count }}次，累计{{ monitorData.total_duration }}秒
                <template v-if="monitorAnalysis.behavior_tags.length > 0">
                  · 包含 {{ monitorAnalysis.behavior_tags.map(t => behaviorTagText(t)).join('、') }}
                </template>
              </div>
            </div>
          </template>
          
          <!-- medium: 中风险 -->
          <template v-else-if="monitorData.risk_level === 'medium'">
            <el-icon class="risk-icon warning"><WarningFilled /></el-icon>
            <div class="risk-text">
              <div class="risk-title">存在需要关注的行为</div>
              <div class="risk-desc">
                <template v-if="monitorAnalysis.behavior_tags.length > 0">
                  {{ monitorAnalysis.behavior_tags.map(t => behaviorTagText(t)).join('、') }}
                </template>
                <template v-else>
                  离开{{ monitorData.leave_count }}次，累计{{ monitorData.total_duration }}秒
                </template>
              </div>
            </div>
          </template>
          
          <!-- high: 高风险 -->
          <template v-else-if="monitorData.risk_level === 'high'">
            <el-icon class="risk-icon danger"><Close /></el-icon>
            <div class="risk-text">
              <div class="risk-title">建议重点人工复核</div>
              <div class="risk-desc">
                <template v-if="monitorAnalysis.behavior_tags.length > 0">
                  {{ monitorAnalysis.behavior_tags.map(t => behaviorTagText(t)).join('、') }}
                </template>
                <template v-else>
                  离开{{ monitorData.leave_count }}次，累计{{ monitorData.total_duration }}秒
                </template>
              </div>
            </div>
          </template>
        </div>

        <!-- S8.4.5: 主要原因结构化列表（HR 可读） -->
        <div v-if="riskReasonList.length > 0" class="risk-reasons">
          <div class="risk-reasons-title">主要原因：</div>
          <div v-for="(reason, idx) in riskReasonList" :key="idx" class="risk-reason-item">
            {{ reason }}
          </div>
        </div>
        
        <!-- S8.4.5: 系统审核建议（辅助 HR 判断，非作弊判定） -->
        <div v-if="monitorAnalysis.review_suggestion" class="review-suggestion">
          <el-alert
            title="💡 审核建议"
            :description="monitorAnalysis.review_suggestion"
            :type="getReasonAlertType(monitorData.risk_level)"
            :closable="false"
            show-icon
            variant="light"
          />
        </div>
      </el-card>
      
      <!-- 监考信息卡片 -->
      <el-card v-if="monitorData.has_monitor_data" class="monitor-card" style="margin-bottom: 16px">
        <template #header>
          <div class="card-header-with-toggle">
            <span class="card-title">监考信息</span>
            <el-tag :type="riskLevelTagType(monitorData.risk_level)" size="small">
              {{ riskLevelText(monitorData.risk_level) }}
            </el-tag>
          </div>
        </template>
        <el-row :gutter="16" class="monitor-stats-row">
          <el-col :xs="24" :sm="12" :md="8" :lg="8" :xl="8" class="monitor-stat-col">
            <el-statistic
              title="风险等级"
              :value="riskLevelText(monitorData.risk_level)"
            >
              <template #value>
                <el-tag :type="riskLevelTagType(monitorData.risk_level)" effect="dark" size="large">
                  {{ riskLevelText(monitorData.risk_level) }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="8" :xl="8" class="monitor-stat-col">
            <el-statistic
              title="离开次数"
              :value="monitorData.leave_count"
              suffix="次"
            />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="8" :xl="8" class="monitor-stat-col">
            <el-statistic
              title="累计离开时长"
              :value="monitorData.total_duration"
              suffix="秒"
            />
          </el-col>
        </el-row>
        <!-- S8.4.3-b: 异常行为时间线 -->
        <template v-if="monitorData.events && monitorData.events.length > 0">
          <el-divider content-position="left">
            <span style="font-size: 13px; color: #606266;">异常行为时间线（共 {{ monitorData.events.length }} 条）</span>
          </el-divider>
          <el-timeline class="event-timeline" :reverse="false">
            <el-timeline-item
              v-for="(event, index) in monitorData.events"
              :key="index"
              :timestamp="formatEventTimeShort(event.timestamp)"
              :type="getTimelineType(event)"
              :hollow="isNormalEvent(event)"
            >
              <div class="timeline-event" :class="{ 'timeline-event-mobile': isMobile }">
                <!-- 移动端：垂直布局 -->
                <div class="timeline-event-header">
                  <el-tag :type="eventTypeTag(event.type)" size="small">
                    {{ eventIcon(event.type) }} {{ eventTypeText(event.type) }}
                  </el-tag>
                  <span v-if="event.duration" class="timeline-duration">
                    持续{{ formatDurationMs(event.duration) }}
                  </span>
                </div>
                <!-- S8.4.2: 异常标签展示 -->
                <div v-if="hasEventTags(event)" class="timeline-tags">
                  <el-tag
                    v-for="tag in event.tags"
                    :key="tag"
                    :type="behaviorTagType(tag)"
                    size="small"
                    style="margin-right: 4px; margin-top: 4px"
                  >
                    {{ behaviorTagText(tag) }}
                  </el-tag>
                </div>
                <!-- S8.4.5: 详情说明（事件 detail 或按类型生成的默认描述） -->
                <template v-if="isMobile">
                  <el-collapse
                    :model-value="getEventCollapse(index)"
                    @update:model-value="(val) => setEventCollapse(index, val)"
                    class="timeline-collapse"
                  >
                    <el-collapse-item :name="'detail-' + index">
                      <template #title>
                        <span class="timeline-detail-toggle">查看详情</span>
                      </template>
                      <div v-if="eventDescription(event)" class="timeline-detail">{{ eventDescription(event) }}</div>
                      <div v-else class="timeline-detail text-muted">无详细描述</div>
                    </el-collapse-item>
                  </el-collapse>
                </template>
                <div v-else-if="eventDescription(event)" class="timeline-detail">{{ eventDescription(event) }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
          
          <!-- 原始数据折叠查看 -->
          <el-collapse class="raw-data-collapse" v-model="rawDataCollapse">
            <el-collapse-item name="raw">
              <template #title>
                <span class="collapse-title">查看原始数据（表格形式）</span>
              </template>
              <el-table :data="monitorData.events" border stripe size="small">
                <el-table-column label="序号" type="index" width="60" />
                <el-table-column prop="timestamp" label="时间" width="180">
                  <template #default="{ row }">
                    {{ formatEventTime(row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column prop="type" label="事件类型" width="150">
                  <template #default="{ row }">
                    <el-tag :type="eventTypeTag(row.type)" size="small">
                      {{ eventIcon(row.type) }} {{ eventTypeText(row.type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="duration" label="持续时间" width="100">
                  <template #default="{ row }">
                    {{ row.duration ? (row.duration >= 1000 ? (row.duration / 1000).toFixed(1) + '秒' : row.duration + '毫秒') : '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="异常标签" width="160">
                  <template #default="{ row }">
                    <template v-if="hasEventTags(row)">
                      <el-tag
                        v-for="tag in row.tags"
                        :key="tag"
                        :type="behaviorTagType(tag)"
                        size="small"
                        style="margin-right: 4px"
                      >
                        {{ behaviorTagText(tag) }}
                      </el-tag>
                    </template>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ row.detail || '-' }}
                  </template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </template>
        <el-empty v-else description="暂无异常行为记录" :image-size="60" />
      </el-card>
      <el-card v-else style="margin-bottom: 16px">
        <template #header>
          <span class="card-title">监考信息</span>
        </template>
        <div class="monitor-empty">
          <el-empty description="暂无监考记录（该考试未开启监考功能）" :image-size="80" />
        </div>
      </el-card>

      <!-- 监考分析卡片（新增） -->
      <el-card v-if="monitorAnalysis.has_analysis" class="monitor-analysis-card" style="margin-bottom: 16px">
        <template #header>
          <div class="card-header-with-toggle">
            <span class="card-title">监考分析</span>
            <el-tag :type="riskLevelTagType(monitorData.risk_level)" size="small" effect="dark">
              {{ riskLevelText(monitorData.risk_level) }}
            </el-tag>
          </div>
        </template>
        <!-- 核心指标 -->
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6" class="monitor-analysis-col">
            <el-statistic
              title="考试时长"
              :value="formatDuration(monitorAnalysis.exam_duration)"
            />
          </el-col>
          <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6" class="monitor-analysis-col">
            <el-statistic
              title="离开占比"
              :value="monitorAnalysis.leave_ratio"
              suffix="%"
              :precision="2"
            />
          </el-col>
          <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6" class="monitor-analysis-col">
            <el-statistic
              title="最长离开"
              :value="monitorAnalysis.max_single_duration"
              suffix="秒"
            />
          </el-col>
          <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6" class="monitor-analysis-col">
            <el-statistic
              title="平均离开"
              :value="monitorAnalysis.average_leave_duration"
              suffix="秒"
              :precision="1"
            />
          </el-col>
        </el-row>
        
        <!-- S8.4.2: 异常行为标签 -->
        <template v-if="monitorAnalysis.behavior_tags && monitorAnalysis.behavior_tags.length > 0">
          <el-divider content-position="left">
            <span style="font-size: 13px; color: #606266;">异常行为识别</span>
          </el-divider>
          <div class="behavior-tags-section">
            <el-tag
              v-for="tag in monitorAnalysis.behavior_tags"
              :key="tag"
              :type="behaviorTagType(tag)"
              effect="dark"
              size="default"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ behaviorTagText(tag) }}
            </el-tag>
          </div>
        </template>
        
        <!-- S8.4.2: 行为详情列表 -->
        <template v-if="monitorAnalysis.behavior_details && monitorAnalysis.behavior_details.length > 0">
          <el-divider content-position="left">
            <span style="font-size: 13px; color: #606266;">异常行为详情</span>
          </el-divider>
          <el-table :data="monitorAnalysis.behavior_details" border stripe size="small">
            <el-table-column prop="time" label="时间" width="120" />
            <el-table-column prop="duration" label="时长" width="100" />
            <el-table-column label="行为标签" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="(tagText, idx) in row.tag_texts"
                  :key="idx"
                  :type="behaviorTagType(row.tags[idx])"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ tagText }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </template>
        
        <!-- 风险原因说明 -->
        <el-divider content-position="left">风险原因说明</el-divider>
        <div class="risk-reason">
          <el-alert
            :title="monitorAnalysis.risk_reason || '暂无详细说明'"
            :type="getReasonAlertType(monitorData.risk_level)"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 评分结果展示 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6">
          <el-card class="score-card">
            <el-statistic
              title="AI评分"
              :value="detail.total_score || 0"
              :precision="1"
            />
            <div class="score-detail">
              <span class="score-sub">客观题: {{ detail.auto_score || 0 }}</span>
              <span class="score-sub">AI简答题: {{ detail.ai_score || 0 }}</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6">
          <el-card class="score-card">
            <template v-if="detail.review_score !== null && detail.review_score !== undefined">
              <el-statistic
                title="HR复核分数"
                :value="detail.review_score"
                :precision="1"
              />
              <div class="score-status">
                <el-tag type="warning" size="small">HR已复核</el-tag>
              </div>
            </template>
            <template v-else>
              <el-statistic title="HR复核分数" value="—" />
              <div class="score-status">
                <el-tag type="info" size="small">暂无复核</el-tag>
              </div>
            </template>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6">
          <el-card class="score-card final-score">
            <el-statistic
              title="最终成绩"
              :value="finalScore"
              :precision="1"
              :class="{ 'pass': finalPassed, 'fail': finalPassed === false }"
            />
            <div class="score-status">
              <el-tag v-if="finalPassed !== null && finalPassed !== undefined" :type="finalPassed ? 'success' : 'danger'" size="small">
                {{ finalPassed ? '及格' : '不及格' }}
              </el-tag>
              <el-tag v-if="detail.review_score !== null && detail.review_score !== undefined" type="warning" size="small" style="margin-left: 4px">
                取HR复核
              </el-tag>
              <el-tag v-else type="info" size="small" style="margin-left: 4px">
                取AI评分
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="6" :xl="6">
          <el-card>
            <template #header>
              <span class="card-title">HR复核操作</span>
            </template>
            <el-form :model="reviewForm" label-width="90px" size="small">
              <el-form-item label="复核分数">
                <el-input-number
                  v-model="reviewForm.review_score"
                  :min="0"
                  :max="maxScore"
                  :precision="1"
                  :step="0.5"
                  placeholder="输入复核分数"
                  controls-position="right"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="复核备注">
                <el-input
                  v-model="reviewForm.review_comment"
                  type="textarea"
                  :rows="2"
                  placeholder="修改原因"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="small" :loading="submitting" @click="submitReview">保存复核</el-button>
                <el-button size="small" @click="resetReviewForm">重置</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <!-- AI评分详情（折叠展示） -->
      <el-card style="margin-bottom: 16px">
        <template #header>
          <div class="card-header-with-toggle">
            <span class="card-title">AI评分详情</span>
            <el-tag size="small" type="info">客观题: {{ detail.auto_score || 0 }} | AI简答题: {{ detail.ai_score || 0 }}</el-tag>
          </div>
        </template>
        <el-collapse v-model="activeCollapse">
          <el-collapse-item title="客观题得分详情" name="auto">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="客观题总分">{{ detail.auto_score || 0 }}</el-descriptions-item>
              <el-descriptions-item label="总题数">{{ detail.statistics.total_questions }}</el-descriptions-item>
              <el-descriptions-item label="已答题数">{{ detail.statistics.answered_count }}</el-descriptions-item>
              <el-descriptions-item label="正确题数">{{ detail.statistics.correct_count }}</el-descriptions-item>
            </el-descriptions>
          </el-collapse-item>
          <el-collapse-item title="AI简答题评分详情" name="ai">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="AI评分总分">{{ detail.ai_score || 0 }}</el-descriptions-item>
              <el-descriptions-item label="AI置信度">{{ aiConfidenceText }}</el-descriptions-item>
            </el-descriptions>
            <el-divider content-position="left">AI评分详情</el-divider>
            <el-table :data="aiScoredAnswers" border stripe size="small" v-if="aiScoredAnswers.length > 0">
              <el-table-column prop="question_no" label="题号" width="80" />
              <el-table-column prop="question_content" label="题目" min-width="200" show-overflow-tooltip />
              <el-table-column prop="ai_score" label="AI得分" width="100">
                <template #default="{ row }">
                  <span class="text-success">{{ row.ai_score ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="score" label="最终得分" width="100">
                <template #default="{ row }">
                  <span>{{ row.score ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="ai_confidence" label="置信度" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.ai_confidence !== null && row.ai_confidence !== undefined" :type="row.ai_confidence >= 0.8 ? 'success' : row.ai_confidence >= 0.6 ? 'warning' : 'danger'" size="small">
                    {{ (row.ai_confidence * 100).toFixed(0) }}%
                  </el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="ai_reason" label="评分原因" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <span>{{ row.ai_reason || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无AI评分详情" :image-size="80" />
          </el-collapse-item>
        </el-collapse>
      </el-card>

      <!-- 评分状态和时间 -->
      <el-card style="margin-bottom: 16px">
        <template #header>
          <span class="card-title">评分状态</span>
        </template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="评分状态">
            <el-tag :type="statusTagType(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="评分类型">
            <el-tag :type="gradingTypeTag(detail.grading_type)">{{ gradingTypeText(detail.grading_type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ detail.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ detail.complete_time || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.error_message" label="错误信息" :span="4">
            <span style="color: #f56c6c">{{ detail.error_message }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 统计信息 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="总题数" :value="detail.statistics.total_questions" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="已答题数" :value="detail.statistics.answered_count" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="正确题数" :value="detail.statistics.correct_count" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-statistic title="正确率" :value="detail.statistics.correct_rate" :precision="1" suffix="%" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 答题详情 -->
      <el-card>
        <template #header>
          <span class="card-title">答题详情</span>
        </template>
        <el-table :data="detail.answers" border stripe>
          <el-table-column prop="question_no" label="题号" width="80" />
          <el-table-column prop="question_type" label="题型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ questionTypeText(row.question_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="question_content" label="题目" min-width="200" show-overflow-tooltip />
          <el-table-column label="选项/答案" min-width="200">
            <template #default="{ row }">
              <div v-if="row.options" class="options-list">
                <div v-for="(opt, idx) in row.options" :key="idx" class="option-item">
                  <span class="option-label">{{ String.fromCharCode(65 + idx) }}.</span>
                  <span>{{ typeof opt === 'string' ? opt : (opt.content || opt.label || '') }}</span>
                </div>
              </div>
              <div v-else class="text-content">{{ row.question_content }}</div>
            </template>
          </el-table-column>
          <el-table-column label="候选人答案" width="150">
            <template #default="{ row }">
              <span :class="{ 'correct': row.is_correct, 'wrong': row.is_correct === false }">
                {{ row.candidate_answer || '未作答' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="标准答案" width="120">
            <template #default="{ row }">
              <span class="correct">{{ row.standard_answer || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="AI评分" width="90">
            <template #default="{ row }">
              <span :class="{ 'text-success': row.is_correct, 'text-danger': row.is_correct === false }">
                {{ row.score ?? '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="HR复核得分" width="100">
            <template #default="{ row }">
              <span v-if="detail.review_score !== null && detail.review_score !== undefined" class="text-warning">
                {{ row.score ?? '-' }}
              </span>
              <span v-else class="text-muted">{{ row.score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="full_score" label="满分" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag
                v-if="row.score_level"
                :type="scoreLevelTagType(row.score_level)"
                size="small"
              >
                {{ scoreLevelText(row.score_level) }}
              </el-tag>
              <el-tag
                v-else-if="row.is_correct !== null && row.is_correct !== undefined"
                :type="row.is_correct ? 'success' : 'danger'"
                size="small"
              >
                {{ row.is_correct ? '正确' : '错误' }}
              </el-tag>
              <el-tag v-else type="info" size="small">未评分</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <template v-else>
      <el-card>
        <el-empty :description="errorMessage || '成绩详情加载失败'">
          <el-button type="primary" @click="fetchDetail">重新加载</el-button>
        </el-empty>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, WarningFilled, Close } from '@element-plus/icons-vue'
import { gradingResultApi } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const detail = ref(null)
const errorMessage = ref('')
const activeCollapse = ref([])
const monitorCollapse = ref([])
const rawDataCollapse = ref([])  // S8.4.3-b: 原始数据折叠
const isMobile = ref(false)  // S8.4.3-c: 移动端判断

// S8.4.3-c: 响应式窗口大小监听
function updateIsMobile() {
  isMobile.value = window.innerWidth <= 768
}
updateIsMobile()
window.addEventListener('resize', updateIsMobile)

const reviewForm = reactive({
  review_score: null,
  review_comment: '',
})

const examRecordId = computed(() => parseInt(route.params.examRecordId))

// 监考数据（兼容历史数据无监考的情况）
const monitorData = computed(() => {
  if (!detail.value || !detail.value.monitor_data) {
    return {
      has_monitor_data: false,
      risk_level: 'normal',
      leave_count: 0,
      total_duration: 0,
      events: [],
    }
  }
  return detail.value.monitor_data
})

// 监考分析数据（兼容历史数据无分析的情况）
const monitorAnalysis = computed(() => {
  if (!detail.value || !detail.value.monitor_analysis) {
    return {
      has_analysis: false,
      exam_duration: 0,
      leave_ratio: 0.0,
      max_single_duration: 0,
      average_leave_duration: 0.0,
      risk_reason: '',
      behavior_tags: [],
      behavior_details: [],
      review_suggestion: '',
    }
  }
  return detail.value.monitor_analysis
})

/**
 * S8.4.5: 风险主要原因结构化列表（HR 可读）
 * 数据来源：monitorData.events + monitorAnalysis（max_single_duration / risk_reason）
 * normal 级别不展示原因；数据缺失时兜底显示 risk_reason
 */
const riskReasonList = computed(() => {
  const d = monitorData.value
  const a = monitorAnalysis.value
  if (!d.has_monitor_data || d.risk_level === 'normal') return []

  const reasons = []
  const events = Array.isArray(d.events) ? d.events : []

  // 1. 离开概况
  if (d.leave_count > 0) {
    reasons.push(`⚠️ 共离开考试页面 ${d.leave_count} 次，累计 ${formatDuration(d.total_duration)}`)
  }

  // 2. 单次超长离开
  const maxSingle = a.max_single_duration || 0
  if (maxSingle >= 300) {
    reasons.push(`⚠️ 存在一次超过5分钟的离开（最长 ${formatDuration(maxSingle)}）`)
  }

  // 3. 网络异常关联
  const networkCount = events.filter(
    (e) => e.type === 'network_offline' || (Array.isArray(e.tags) && e.tags.includes('network_related'))
  ).length
  if (networkCount > 0) {
    reasons.push(`📡 其中 ${networkCount} 次与网络异常相关`)
  }

  // 4. 异常中断恢复
  const recoveredCount = events.filter((e) => e.type === 'leave_recovered').length
  if (recoveredCount > 0) {
    reasons.push(`🔄 存在 ${recoveredCount} 次考试页面异常关闭后恢复`)
  }

  // 5. 高频快速切换
  if (Array.isArray(a.behavior_tags) && a.behavior_tags.includes('frequent_leave')) {
    reasons.push('⚠️ 存在短时间内频繁切换考试页面的行为')
  }

  // 6. 刷新尝试
  const refreshCount = events.filter((e) => e.type === 'refresh_attempt').length
  if (refreshCount > 0) {
    reasons.push(`🔄 检测到 ${refreshCount} 次页面刷新尝试`)
  }

  // 兜底：以上均未命中时使用后端 risk_reason
  if (reasons.length === 0 && a.risk_reason) {
    reasons.push(`⚠️ ${a.risk_reason}`)
  }
  return reasons
})

// 格式化时长（秒 → 友好格式）
function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0秒'
  if (seconds < 60) return seconds + '秒'
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return secs > 0 ? `${mins}分${secs}秒` : `${mins}分`
  }
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return mins > 0 ? `${hours}时${mins}分` : `${hours}时`
}

// 获取风险原因对应的Alert类型
function getReasonAlertType(riskLevel) {
  const typeMap = {
    normal: 'success',
    low: 'info',
    medium: 'warning',
    high: 'error',
  }
  return typeMap[riskLevel] || 'info'
}

// 计算最终显示分数：如果有HR复核分数，显示复核分数；否则显示系统总分
const finalScore = computed(() => {
  if (!detail.value) return 0
  if (detail.value.review_score !== null && detail.value.review_score !== undefined) {
    return detail.value.review_score
  }
  return detail.value.total_score || 0
})

// 计算最终及格状态
const finalPassed = computed(() => {
  if (!detail.value) return null
  if (detail.value.review_score !== null && detail.value.review_score !== undefined) {
    // 如果有复核分数，检查是否及格
    // 默认60分及格，或者使用原有的passed判断
    return detail.value.review_score >= 60
  }
  return detail.value.passed
})

// AI评分详情相关数据
const aiScoredAnswers = computed(() => {
  if (!detail.value || !detail.value.answers) return []
  return detail.value.answers.filter(a => a.ai_score !== null && a.ai_score !== undefined)
})

const aiConfidenceText = computed(() => {
  const aiAnswers = aiScoredAnswers.value
  if (aiAnswers.length === 0) return '-'
  const totalConfidence = aiAnswers.reduce((sum, a) => sum + (a.ai_confidence || 0), 0)
  const avgConfidence = totalConfidence / aiAnswers.length
  return (avgConfidence * 100).toFixed(1) + '%'
})

// 计算试卷总分（用于复核分数上限）
const maxScore = computed(() => {
  if (!detail.value || !detail.value.answers) return 100
  return detail.value.answers.reduce((sum, a) => sum + (a.full_score || 0), 0)
})

const statusText = (s) => ({ pending: '待评分', grading: '评分中', completed: '已完成', failed: '评分失败' }[s] || s)
const statusTagType = (s) => ({ pending: 'info', grading: 'warning', completed: 'success', failed: 'danger' }[s] || 'info')
const gradingTypeText = (t) => ({ auto: '自动', ai: 'AI', hybrid: '混合' }[t] || t)
const gradingTypeTag = (t) => ({ auto: '', ai: 'warning', hybrid: 'info' }[t] || '')
const questionTypeText = (t) => ({
  single_choice: '单选',
  multiple_choice: '多选',
  true_false: '判断',
  short_answer: '简答',
}[t] || t)

const scoreLevelText = (level) => ({
  full_correct: '完全正确',
  partial_correct: '部分正确',
  incorrect: '错误',
}[level] || '-')

const scoreLevelTagType = (level) => ({
  full_correct: 'success',
  partial_correct: 'warning',
  incorrect: 'danger',
}[level] || 'info')

// 监考风险等级映射
const riskLevelText = (level) => ({
  normal: '正常',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
}[level] || '未知')

const riskLevelTagType = (level) => ({
  normal: 'success',
  low: 'warning',
  medium: 'warning',
  high: 'danger',
}[level] || 'info')

// S8.4.5: 监考事件中文映射配置（label/icon/type 三元组，未知事件兜底显示"其他监考事件"）
const monitorEventMap = {
  // S8.3.x 核心监考事件
  exam_leave: { label: '离开考试页面', icon: '⚠️', type: 'warning' },
  exam_return: { label: '返回考试页面', icon: '✅', type: 'success' },
  // S8.4.4: 异常中断恢复（浏览器被系统回收后重新进入）
  leave_recovered: { label: '异常中断恢复', icon: '🔄', type: 'warning' },
  // S8.4.1 环境采集事件
  orientation_change: { label: '屏幕方向变化', icon: '📱', type: 'info' },
  network_offline: { label: '网络异常', icon: '📡', type: 'danger' },
  network_online: { label: '网络恢复', icon: '📡', type: 'success' },
  refresh_attempt: { label: '页面刷新尝试', icon: '🔄', type: 'danger' },
  // 传统事件（历史数据兼容）
  page_leave: { label: '离开考试页面', icon: '⚠️', type: 'warning' },
  page_enter: { label: '返回考试页面', icon: '✅', type: 'success' },
  window_blur: { label: '窗口失焦', icon: '⚠️', type: 'warning' },
  window_focus: { label: '窗口聚焦', icon: '✅', type: 'success' },
  tab_switch: { label: '切换标签页', icon: '⚠️', type: 'danger' },
  copy: { label: '复制行为', icon: '📋', type: 'info' },
  paste: { label: '粘贴行为', icon: '📋', type: 'info' },
}

// 未知事件兜底配置（禁止显示 undefined 或原始英文名）
const UNKNOWN_EVENT_CONFIG = { label: '其他监考事件', icon: '📋', type: 'info' }

const getEventConfig = (type) => monitorEventMap[type] || UNKNOWN_EVENT_CONFIG

const eventTypeText = (type) => getEventConfig(type).label
const eventTypeTag = (type) => getEventConfig(type).type
const eventIcon = (type) => getEventConfig(type).icon

/**
 * S8.4.5: 生成事件的详情说明（HR 可读）
 * 优先使用事件自带 detail，其次按类型生成默认描述
 */
function eventDescription(event) {
  if (!event) return ''
  if (event.detail) return event.detail

  const durationText = event.duration ? formatDurationMs(event.duration) : ''
  switch (event.type) {
    case 'leave_recovered':
      return `浏览器后台恢复，离开${durationText || '一段时间'}（上次会话异常终止，系统已自动补记）`
    case 'network_offline':
      return '考试期间网络连接中断'
    case 'network_online':
      return '网络连接已恢复'
    case 'orientation_change': {
      const orientText = (o) => (o === 'portrait' ? '竖屏' : o === 'landscape' ? '横屏' : o)
      if (event.from && event.to) {
        return `屏幕方向从${orientText(event.from)}切换为${orientText(event.to)}`
      }
      return '检测到屏幕方向发生变化'
    }
    case 'refresh_attempt':
      return event.source === 'bfcache_restore'
        ? '检测到页面从浏览器缓存恢复（疑似刷新）'
        : '检测到页面刷新行为'
    default:
      return ''
  }
}

// S8.4.2: 行为标签映射
const behaviorTagText = (tag) => ({
  rapid_leave_return: '⚡ 快速返回',
  long_leave: '⏱️ 长时间离开',
  frequent_leave: '📊 高频离开',
  network_related: '📡 网络相关',
  refresh_attempt: '🔄 刷新尝试',
}[tag] || tag)

const behaviorTagType = (tag) => ({
  rapid_leave_return: 'warning',
  long_leave: 'danger',
  frequent_leave: 'warning',
  network_related: 'info',
  refresh_attempt: 'danger',
}[tag] || '')

// S8.4.2: 检查事件是否有标签
function hasEventTags(event) {
  return event && event.tags && event.tags.length > 0
}

// 格式化事件时间
function formatEventTime(timestamp) {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return String(timestamp)
  }
}

// S8.4.3-b: 时间线短时间格式（HH:mm:ss）
function formatEventTimeShort(timestamp) {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    const hh = String(date.getHours()).padStart(2, '0')
    const mm = String(date.getMinutes()).padStart(2, '0')
    const ss = String(date.getSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  } catch {
    return '-'
  }
}

// S8.4.3-b: 格式化毫秒时长
function formatDurationMs(ms) {
  if (!ms || ms <= 0) return ''
  if (ms < 1000) return ms + '毫秒'
  const seconds = ms / 1000
  if (seconds < 60) return seconds.toFixed(1) + '秒'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs > 0 ? `${mins}分${secs}秒` : `${mins}分`
}

// S8.4.3-b: 时间线类型（根据事件标签返回颜色）
function getTimelineType(event) {
  const tags = event?.tags || []
  const type = event?.type
  // 网络相关用蓝色
  if (tags.includes('network_related') || type === 'network_offline' || type === 'network_online') {
    return 'primary'
  }
  // 长时间离开/刷新用红色
  if (tags.includes('long_leave') || tags.includes('refresh_attempt')) {
    return 'danger'
  }
  // 高频离开用橙色
  if (tags.includes('frequent_leave')) {
    return 'warning'
  }
  // 快速返回用黄色
  if (tags.includes('rapid_leave_return')) {
    return 'warning'
  }
  // 离开事件默认蓝色
  if (type === 'exam_leave' || type === 'page_leave') {
    return 'primary'
  }
  // 返回/恢复成功用绿色
  if (type === 'exam_return' || type === 'page_enter' || type === 'network_online') {
    return 'success'
  }
  return 'info'
}

// S8.4.3-b: 是否为普通事件（无标签，用于空心圆显示）
function isNormalEvent(event) {
  return !event?.tags || event.tags.length === 0
}

// S8.4.3-c: 移动端事件详情折叠状态
const eventCollapseStates = ref({})
function getEventCollapse(index) {
  const key = 'detail-' + index
  if (!eventCollapseStates.value[key]) {
    eventCollapseStates.value[key] = []
  }
  return eventCollapseStates.value[key]
}
function setEventCollapse(index, val) {
  const key = 'detail-' + index
  eventCollapseStates.value[key] = val
}

function goBack() {
  router.push('/admin/grading')
}

function initReviewForm() {
  if (detail.value) {
    reviewForm.review_score = detail.value.review_score
    reviewForm.review_comment = detail.value.review_comment || ''
  }
}

function resetReviewForm() {
  initReviewForm()
  ElMessage.info('已重置为当前数据')
}

async function submitReview() {
  if (reviewForm.review_score === null || reviewForm.review_score === undefined) {
    ElMessage.warning('请输入复核分数')
    return
  }

  if (reviewForm.review_score < 0) {
    ElMessage.warning('复核分数不能为负数')
    return
  }

  if (reviewForm.review_score > maxScore.value) {
    ElMessage.warning(`复核分数不能超过试卷满分 ${maxScore.value}`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认保存HR复核分数 ${reviewForm.review_score} 分？保存后将作为最终成绩显示。`,
      '确认保存',
      {
        confirmButtonText: '确认保存',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    const res = await gradingResultApi.updateHRReview(examRecordId.value, {
      review_score: reviewForm.review_score,
      review_comment: reviewForm.review_comment,
    })
    detail.value = res.data
    ElMessage.success('HR复核保存成功')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

async function fetchDetail() {
  if (!examRecordId.value && examRecordId.value !== 0) {
    errorMessage.value = '无效的考试记录ID'
    detail.value = null
    loading.value = false
    return
  }

  loading.value = true
  errorMessage.value = ''
  detail.value = null
  try {
    const res = await gradingResultApi.getResultDetail(examRecordId.value)
    detail.value = res.data
    errorMessage.value = ''
    initReviewForm()
  } catch (e) {
    detail.value = null
    errorMessage.value = e.response?.data?.detail || e.message || '成绩详情加载失败，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)

// S8.4.3-d: 路由参数变化监听，确保连续切换详情时数据正确刷新
watch(() => route.params.examRecordId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    fetchDetail()
  }
})

// S8.4.3-c: 清理窗口大小监听
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateIsMobile)
})
</script>

<style scoped>
/* S8.4.3-c: 页面容器默认样式 */
.grading-result-detail {
  padding: 0 8px;
  max-width: 100%;
  overflow-x: hidden;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
}

.card-header-with-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-card {
  text-align: center;
  padding: 16px 0;
}

.score-card.final-score {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.score-detail {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.score-sub {
  font-size: 12px;
  color: #909399;
}

.score-status {
  margin-top: 8px;
}

.stat-card {
  text-align: center;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.option-item {
  font-size: 13px;
  color: #606266;
}

.option-label {
  font-weight: 600;
  margin-right: 4px;
}

.text-content {
  font-size: 13px;
  color: #606266;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.correct {
  color: #67c23a;
  font-weight: 500;
}

.wrong {
  color: #f56c6c;
}

.text-success {
  color: #67c23a;
  font-weight: 600;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.text-warning {
  color: #e6a23c;
  font-weight: 600;
}

.text-muted {
  color: #c0c4cc;
}

.pass {
  color: #67c23a;
}

.fail {
  color: #f56c6c;
}

/* 监考信息卡片样式 */
.monitor-card {
  border-left: 4px solid #409eff;
}

.monitor-stat-col {
  text-align: center;
}

.monitor-empty {
  padding: 16px 0;
}

.collapse-title {
  font-weight: 500;
  font-size: 13px;
  color: #606266;
}

/* 监考分析卡片样式 */
.monitor-analysis-card {
  border-left: 4px solid #67c23a;
}

.monitor-analysis-col {
  text-align: center;
  padding: 8px 0;
}

.risk-reason {
  margin-top: 8px;
}

.risk-reason .el-alert {
  line-height: 1.8;
}

/* S8.4.2: 异常行为标签区样式 */
.behavior-tags-section {
  padding: 4px 0;
  min-height: 36px;
}

/* S8.4.3-b: 监考风险摘要卡片样式 */
.risk-summary-card {
  border-left: 4px solid #409eff;
}

.risk-summary-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 8px 0;
  border-radius: 8px;
  transition: background-color 0.3s;
}

.risk-summary-content.risk-normal {
  background-color: #f0f9eb;
  padding: 16px;
  border-radius: 8px;
}
.risk-summary-content.risk-low {
  background-color: #fdf6ec;
  padding: 16px;
  border-radius: 8px;
}
.risk-summary-content.risk-medium {
  background-color: #fdf6ec;
  padding: 16px;
  border-radius: 8px;
  border-left: 3px solid #e6a23c;
}
.risk-summary-content.risk-high {
  background-color: #fef0f0;
  padding: 16px;
  border-radius: 8px;
  border-left: 3px solid #f56c6c;
}

.risk-icon {
  font-size: 40px;
  flex-shrink: 0;
}
.risk-icon.success { color: #67c23a; }
.risk-icon.warning { color: #e6a23c; }
.risk-icon.danger { color: #f56c6c; }

.risk-text {
  flex: 1;
  min-width: 0;
}

.risk-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.risk-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

/* S8.4.5: 主要原因结构化列表 */
.risk-reasons {
  margin-top: 12px;
  padding: 10px 14px;
  background: #f8f9fb;
  border-radius: 6px;
}

.risk-reasons-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.risk-reason-item {
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
  padding-left: 4px;
}

.review-suggestion {
  margin-top: 12px;
}

/* S8.4.3-b: 时间线样式 */
.event-timeline {
  padding: 8px 0;
}

.timeline-event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.timeline-duration {
  font-size: 12px;
  color: #909399;
}

.timeline-tags {
  margin-bottom: 4px;
}

.timeline-detail {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.raw-data-collapse {
  margin-top: 12px;
}

/* S8.4.3-c: 移动端详情折叠 */
.timeline-collapse {
  margin-top: 6px;
}
.timeline-detail-toggle {
  font-size: 12px;
  color: #409eff;
}

/* S8.4.3-c: 移动端时间线事件样式 */
.timeline-event-mobile {
  padding: 4px 0;
}
.timeline-event-mobile .timeline-event-header {
  flex-wrap: wrap;
  gap: 6px;
}
.timeline-event-mobile .timeline-duration {
  display: block;
  width: 100%;
  margin-top: 2px;
}
.timeline-event-mobile .timeline-tags .el-tag {
  margin-bottom: 4px;
}
.timeline-event-mobile .timeline-detail {
  font-size: 12px;
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* S8.4.3-c: 移动端适配优化 - 768px以下 */
@media (max-width: 768px) {
  .monitor-stat-col {
    margin-bottom: 12px;
  }
  .monitor-analysis-col {
    margin-bottom: 12px;
  }
  
  /* 统计卡片纵向排列 */
  .monitor-card .el-row {
    flex-direction: column;
  }
  .monitor-card .el-col {
    max-width: 100%;
    margin-bottom: 8px;
  }
  
  /* 风险摘要响应式 */
  .risk-summary-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .risk-icon {
    font-size: 32px;
  }
  .risk-title {
    font-size: 16px;
  }
  
  /* 时间线移动端优化 */
  .event-timeline {
    padding-left: 0;
  }
  .event-timeline .el-timeline-item {
    padding-bottom: 14px;
  }
  
  /* 监考统计移动端纵向 */
  .monitor-stats-row .el-col {
    flex: 0 0 100%;
    max-width: 100%;
    margin-bottom: 12px;
  }
  
  /* 基本信息卡片移动端 */
  .grading-result-detail .el-descriptions {
    font-size: 13px;
  }
  
  /* 标签自动换行 */
  .behavior-tags-section .el-tag {
    margin-bottom: 8px;
  }
  
  /* 审核建议移动端 */
  .review-suggestion .el-alert {
    font-size: 12px;
    padding: 8px 12px;
  }
}

/* S8.4.3-c: 480px 以下进一步优化 */
@media (max-width: 480px) {
  .risk-summary-content {
    padding: 12px;
  }
  .risk-icon {
    font-size: 28px;
  }
  .risk-title {
    font-size: 15px;
  }
  .risk-desc {
    font-size: 12px;
  }
  
  /* 卡片头部紧凑 */
  .el-card__header {
    padding: 10px 12px;
  }
  .el-card__body {
    padding: 12px;
  }
  
  /* 统计数字字号缩小 */
  .el-statistic__head {
    font-size: 12px;
  }
  .el-statistic__content {
    font-size: 18px;
  }
  
  /* 时间线事件头部换行 */
  .timeline-event-header {
    flex-wrap: wrap;
    gap: 4px;
  }
  
  /* 标签换行优化 */
  .timeline-tags .el-tag {
    font-size: 11px;
    padding: 0 6px;
    height: 20px;
    line-height: 18px;
  }
  
  /* 原始数据表格横向滚动 */
  .raw-data-collapse .el-table {
    font-size: 12px;
  }
  
  /* 页面头部紧凑 */
  .el-page-header {
    padding: 8px 0;
  }
}

/* S8.4.3-c: 390px 以下 iPhone SE/iPhone 13 Mini 优化 */
@media (max-width: 390px) {
  .risk-summary-content {
    padding: 10px;
    gap: 8px;
  }
  .risk-icon {
    font-size: 24px;
  }
  .risk-title {
    font-size: 14px;
  }
  .risk-desc {
    font-size: 11px;
    line-height: 1.4;
  }
  
  /* 统计卡片紧凑 */
  .el-statistic__content {
    font-size: 16px;
  }
  .el-statistic__head {
    font-size: 11px;
  }
  
  /* 标签缩小适配 */
  .el-tag {
    font-size: 11px;
    padding: 0 4px;
  }
  
  /* 监考信息卡片 */
  .monitor-card .el-col {
    margin-bottom: 6px;
  }
  
  /* 时间线 */
  .event-timeline .el-timeline-item {
    padding-bottom: 10px;
  }
  
  /* 行为标签 */
  .behavior-tags-section .el-tag {
    font-size: 10px;
    height: 18px;
    line-height: 16px;
    padding: 0 4px;
    margin-right: 4px;
    margin-bottom: 4px;
  }
}

/* S8.4.3-c: 375px 以下极限适配 iPhone SE */
@media (max-width: 375px) {
  .el-card {
    border-radius: 6px;
  }
  .el-card__header {
    padding: 8px 10px;
    font-size: 13px;
  }
  .el-card__body {
    padding: 10px;
  }
  
  /* 风险摘要 */
  .risk-summary-content {
    padding: 8px;
  }
  .risk-icon {
    font-size: 22px;
  }
  .risk-title {
    font-size: 13px;
  }
  .risk-desc {
    font-size: 11px;
  }
  
  /* 监考统计 */
  .el-statistic__content {
    font-size: 15px;
  }
  
  /* 标签最小化 */
  .el-tag {
    font-size: 10px;
    height: 18px;
    line-height: 16px;
  }
  
  /* 时间线节点间距缩小 */
  .event-timeline {
    padding-left: 0;
  }
  .event-timeline .el-timeline-item {
    padding-bottom: 8px;
  }
  
  /* 审核建议 */
  .review-suggestion .el-alert {
    padding: 6px 10px;
    font-size: 11px;
  }
}
</style>
