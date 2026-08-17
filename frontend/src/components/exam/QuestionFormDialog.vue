<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑题目' : '添加题目'"
    width="640px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <!-- 题型选择 -->
      <el-form-item label="题型" prop="type">
        <el-select v-model="form.type" placeholder="请选择题型" @change="handleTypeChange">
          <el-option label="单选题" value="single_choice" />
          <el-option label="简答题" value="short_answer" />
          <el-option label="多选题" value="multiple_choice" disabled />
          <el-option label="判断题" value="true_false" disabled />
        </el-select>
      </el-form-item>

      <!-- 题目内容 -->
      <el-form-item label="题目内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="3"
          placeholder="请输入题目内容"
        />
      </el-form-item>

      <!-- 选项设置（仅单选/多选显示） -->
      <el-form-item
        v-if="form.type === 'single_choice' || form.type === 'multiple_choice'"
        label="选项设置"
        required
      >
        <div class="options-container">
          <div
            v-for="(opt, idx) in form.options"
            :key="idx"
            class="option-row"
          >
            <el-input
              v-model="opt.label"
              :placeholder="`选项 ${String.fromCharCode(65 + idx)}`"
              style="width: 80px"
              maxlength="10"
            />
            <el-input
              v-model="opt.content"
              placeholder="请输入选项内容"
            />
            <el-button
              type="danger"
              link
              :disabled="form.options.length <= 2"
              @click="removeOption(idx)"
            >
              删除
            </el-button>
          </div>
          <el-button
            type="primary"
            link
            :disabled="form.options.length >= 10"
            @click="addOption"
          >
            + 添加选项
          </el-button>
        </div>
      </el-form-item>

      <!-- 正确答案（单选/多选） -->
      <el-form-item
        v-if="form.type === 'single_choice'"
        label="正确答案"
        prop="answer"
        required
      >
        <el-radio-group v-model="form.answer">
          <el-radio
            v-for="opt in form.options"
            :key="opt.label"
            :label="opt.label"
          >
            {{ opt.label }}. {{ opt.content?.slice(0, 20) }}{{ opt.content && opt.content.length > 20 ? '...' : '' }}
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 标准答案（简答题） -->
      <el-form-item
        v-if="form.type === 'short_answer'"
        label="标准答案"
        prop="answer"
      >
        <el-input
          v-model="form.answer"
          type="textarea"
          :rows="4"
          placeholder="输入标准答案，AI 评分时将基于此答案进行语义匹配"
        />
        <div class="hint">支持关键词、关键点描述，AI 将进行语义评分</div>
      </el-form-item>

      <!-- 分值 -->
      <el-form-item label="分值" prop="score">
        <el-input-number
          v-model="form.score"
          :min="0"
          :max="100"
          :precision="1"
        />
        <span class="score-unit">分</span>
      </el-form-item>

      <!-- 排序 -->
      <el-form-item label="排序">
        <el-input-number
          v-model="form.sort_order"
          :min="0"
          :max="999"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存
        </el-button>
        <el-button
          type="success"
          :loading="submitting"
          @click="handleSubmit(true)"
        >
          保存并继续添加
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { questionApi } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  examId: { type: [Number, String], required: true },
  editData: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(props.modelValue)
const submitting = ref(false)
const formRef = ref(null)
const isEdit = ref(false)

const defaultForm = () => ({
  type: 'single_choice',
  content: '',
  options: [
    { label: 'A', content: '' },
    { label: 'B', content: '' },
  ],
  answer: 'A',
  score: 10,
  sort_order: 0,
})

const form = reactive(defaultForm())

const rules = {
  content: [
    { required: true, message: '请输入题目内容', trigger: 'blur' },
    { min: 1, message: '题目内容不能为空', trigger: 'blur' },
  ],
  answer: [
    { required: true, message: '请填写正确答案', trigger: 'change' },
  ],
  score: [
    { required: true, message: '请设置分值', trigger: 'blur' },
  ],
}

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      initForm()
    }
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function initForm() {
  if (props.editData) {
    isEdit.value = true
    Object.assign(form, {
      ...defaultForm(),
      ...props.editData,
      options: props.editData.options
        ? JSON.parse(JSON.stringify(props.editData.options))
        : defaultForm().options,
    })
  } else {
    isEdit.value = false
    Object.assign(form, defaultForm())
  }
}

function handleTypeChange() {
  if (form.type === 'single_choice' || form.type === 'multiple_choice') {
    if (!form.options || form.options.length < 2) {
      form.options = [
        { label: 'A', content: '' },
        { label: 'B', content: '' },
      ]
    }
    if (!form.answer || !form.options.find((o) => o.label === form.answer)) {
      form.answer = form.options[0]?.label || 'A'
    }
  } else if (form.type === 'short_answer') {
    form.answer = ''
  }
}

function addOption() {
  if (form.options.length >= 10) return
  const nextLabel = String.fromCharCode(65 + form.options.length)
  form.options.push({ label: nextLabel, content: '' })
}

function removeOption(idx) {
  if (form.options.length <= 2) return
  form.options.splice(idx, 1)
  form.options.forEach((opt, i) => {
    opt.label = String.fromCharCode(65 + i)
  })
  if (form.answer && !form.options.find((o) => o.label === form.answer)) {
    form.answer = form.options[0]?.label || ''
  }
}

function validateForm() {
  return new Promise((resolve, reject) => {
    formRef.value.validate((valid) => {
      if (!valid) {
        reject(new Error('表单校验失败'))
        return
      }
      if (form.type === 'single_choice' || form.type === 'multiple_choice') {
        const validOptions = form.options.filter((o) => o.content && o.content.trim())
        if (validOptions.length < 2) {
          ElMessage.warning('选项至少需要 2 个，且内容不能为空')
          reject(new Error('选项校验失败'))
          return
        }
        const optionLabels = form.options.map((o) => o.label)
        if (!form.answer || !optionLabels.includes(form.answer)) {
          ElMessage.warning('请选择正确答案')
          reject(new Error('答案校验失败'))
          return
        }
      } else if (form.type === 'short_answer') {
        if (!form.answer || !form.answer.trim()) {
          ElMessage.warning('请填写标准答案')
          reject(new Error('答案校验失败'))
          return
        }
      }
      resolve()
    })
  })
}

async function handleSubmit(continueAdd = false) {
  try {
    await validateForm()
    submitting.value = true

    const payload = {
      type: form.type,
      content: form.content.trim(),
      options:
        form.type === 'single_choice' || form.type === 'multiple_choice'
          ? form.options.map((o) => ({
              label: o.label,
              content: o.content.trim(),
            }))
          : null,
      answer: form.answer.trim(),
      score: Number(form.score),
      sort_order: Number(form.sort_order),
    }

    if (isEdit.value && props.editData?.id) {
      await questionApi.update(props.editData.id, props.examId, payload)
      ElMessage.success('修改成功')
    } else {
      await questionApi.create(props.examId, payload)
      ElMessage.success('添加成功')
    }

    emit('success', payload)

    if (continueAdd) {
      Object.assign(form, {
        type: form.type,
        content: '',
        options:
          form.type === 'single_choice' || form.type === 'multiple_choice'
            ? [
                { label: 'A', content: '' },
                { label: 'B', content: '' },
              ]
            : [],
        answer: form.type === 'short_answer' ? '' : 'A',
        score: 10,
        sort_order: Number(form.sort_order) + 1,
      })
      formRef.value?.clearValidate()
    } else {
      visible.value = false
    }
  } catch (e) {
    if (e.message !== '表单校验失败' && e.message !== '选项校验失败' && e.message !== '答案校验失败') {
      console.error(e)
    }
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  visible.value = false
  formRef.value?.resetFields()
}
</script>

<style scoped>
.options-container {
  width: 100%;
}

.option-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.option-row .el-input:first-child {
  flex-shrink: 0;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.score-unit {
  margin-left: 8px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
