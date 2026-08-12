<template>
  <el-dialog
    v-model="visible"
    title="导入试卷"
    width="560px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="import-exam-dialog">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".json"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :on-remove="handleRemove"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将 JSON 文件拖到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="upload-tip">仅支持 .json 格式，导入后将覆盖当前考试信息和题目</div>
        </template>
      </el-upload>

      <div v-if="importing" class="importing">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>正在导入中，请稍候...</span>
      </div>

      <div v-if="result" class="import-result">
        <el-alert
          :title="result.success ? '导入成功' : '导入失败'"
          :type="result.success ? 'success' : 'error'"
          show-icon
          :closable="false"
        >
          <template #default>
            <div v-if="result.success" class="result-detail">
              <p>✅ 考试名称：{{ result.data?.exam_title || '-' }}</p>
              <p>✅ 导入题目数量：{{ result.data?.imported_count || 0 }}</p>
            </div>
            <div v-else class="result-detail">
              <p>❌ {{ result.message || '未知错误' }}</p>
              <ul v-if="result.errors?.length" class="error-list">
                <li v-for="(err, idx) in result.errors" :key="idx">{{ err }}</li>
              </ul>
            </div>
          </template>
        </el-alert>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button
        type="primary"
        :disabled="!file || importing"
        :loading="importing"
        @click="handleImport"
      >
        开始导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { examApi } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  examId: { type: [Number, String], default: null },
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(false)
const uploadRef = ref(null)
const file = ref(null)
const importing = ref(false)
const result = ref(null)

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      file.value = null
      result.value = null
    }
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function handleFileChange(uploadFile) {
  if (uploadFile && uploadFile.raw) {
    file.value = uploadFile.raw
    result.value = null
  }
}

function handleExceed() {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

function handleRemove() {
  file.value = null
}

function handleClose() {
  visible.value = false
  file.value = null
  result.value = null
  importing.value = false
}

async function handleImport() {
  if (!file.value) {
    ElMessage.warning('请先选择 JSON 文件')
    return
  }
  if (!props.examId) {
    ElMessage.error('缺少考试 ID')
    return
  }
  importing.value = true
  result.value = null
  try {
    const res = await examApi.importExam(props.examId, file.value)
    result.value = { success: true, message: res.message, data: res.data }
    ElMessage.success('导入成功')
    emit('success', res.data)
  } catch (e) {
    const data = e?.response?.data
    result.value = {
      success: false,
      message: data?.message || e?.message || '导入失败',
      errors: data?.data?.errors || [],
    }
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-exam-dialog {
  padding: 16px 0;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.importing {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  color: #409eff;
}

.import-result {
  margin-top: 16px;
}

.result-detail p {
  margin: 4px 0;
}
</style>
