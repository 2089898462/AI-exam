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
      resize="vertical"
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
  font-size: 14px;
  line-height: 1.8;
}
</style>
