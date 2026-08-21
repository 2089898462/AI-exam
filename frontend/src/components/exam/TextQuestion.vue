<template>
  <div class="text-question" :class="{ 'text-question--disabled': disabled }">
    <el-input
      v-model="innerValue"
      type="textarea"
      :rows="5"
      :maxlength="2000"
      :disabled="disabled"
      placeholder="请输入您的答案..."
      show-word-limit
      :autosize="{ minRows: 5, maxRows: 12 }"
      resize="none"
      @input="handleInput"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  question: {
    type: Object,
    required: true,
  },
  modelValue: {
    type: [String, Number],
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const innerValue = ref(String(props.modelValue || ''))

watch(
  () => props.modelValue,
  (val) => {
    innerValue.value = String(val || '')
  }
)

function handleInput() {
  if (!props.disabled) {
    emit('update:modelValue', innerValue.value)
  }
}
</script>

<style scoped>
.text-question {
  width: 100%;
}

.text-question :deep(.el-textarea__inner) {
  font-size: 15px;
  line-height: 1.8;
  padding: 12px 14px;
  border-radius: 10px;
  min-height: 140px;
}

.text-question :deep(.el-textarea__inner::placeholder) {
  color: #c0c4cc;
  font-size: 14px;
}

.text-question :deep(.el-input__count) {
  font-size: 12px;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .text-question :deep(.el-textarea__inner) {
    font-size: 16px;
    line-height: 1.75;
    padding: 12px;
    min-height: 160px;
    /* 防止 iOS 自动缩放 */
    -webkit-text-size-adjust: 100%;
  }

  .text-question :deep(.el-textarea__inner::placeholder) {
    font-size: 15px;
  }
}

@media (max-width: 380px) {
  .text-question :deep(.el-textarea__inner) {
    font-size: 15px;
    min-height: 140px;
  }
}
</style>
