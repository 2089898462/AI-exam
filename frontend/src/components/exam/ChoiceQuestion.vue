<template>
  <div class="choice-question">
    <el-radio-group
      v-if="question.type === 'single_choice' || question.type === 'true_false'"
      v-model="innerValue"
      @change="handleChange"
    >
      <el-radio
        v-for="(option, idx) in parsedOptions"
        :key="idx"
        :value="getOptionValue(option)"
        class="choice-option"
      >
        <span class="option-label">{{ getOptionLabel(option) }}</span>
        <span v-if="getOptionContent(option)" class="option-content">
          {{ getOptionContent(option) }}
        </span>
      </el-radio>
    </el-radio-group>

    <el-checkbox-group
      v-else-if="question.type === 'multiple_choice'"
      v-model="innerValue"
      @change="handleChange"
    >
      <el-checkbox
        v-for="(option, idx) in parsedOptions"
        :key="idx"
        :value="getOptionValue(option)"
        class="choice-option"
      >
        <span class="option-label">{{ getOptionLabel(option) }}</span>
        <span v-if="getOptionContent(option)" class="option-content">
          {{ getOptionContent(option) }}
        </span>
      </el-checkbox>
    </el-checkbox-group>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  question: {
    type: Object,
    required: true,
  },
  modelValue: {
    type: [String, Array],
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const parsedOptions = computed(() => {
  if (!props.question.options) return []
  return props.question.options
})

const innerValue = ref(props.modelValue)

watch(
  () => props.modelValue,
  (val) => {
    innerValue.value = val
  }
)

function getOptionValue(option) {
  if (typeof option === 'object' && option !== null) {
    return option.key !== undefined ? String(option.key) : String(option.value || option.id || '')
  }
  return String(option)
}

function getOptionLabel(option) {
  if (typeof option === 'object' && option !== null) {
    return option.label || option.key || option.value || ''
  }
  return ''
}

function getOptionContent(option) {
  if (typeof option === 'object' && option !== null) {
    return option.content || option.text || ''
  }
  return ''
}

function handleChange() {
  emit('update:modelValue', innerValue.value)
}
</script>

<style scoped>
.choice-question {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.choice-option {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: all 0.2s;
  cursor: pointer;
}

.choice-option:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.choice-option :deep(.el-radio__input),
.choice-option :deep(.el-checkbox__input) {
  margin-right: 10px;
}

.choice-option :deep(.el-radio__input.is-checked + .el-radio__label),
.choice-option :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
  color: #409eff;
}

.choice-option :deep(.el-radio__input.is-checked .el-radio__inner),
.choice-option :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #409eff;
  border-color: #409eff;
}

.option-label {
  font-weight: 600;
  margin-right: 6px;
  color: #303133;
}

.option-content {
  color: #606266;
  line-height: 1.6;
}
</style>
