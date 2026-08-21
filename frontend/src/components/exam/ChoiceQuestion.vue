<template>
  <div class="choice-question" :class="{ 'choice-question--disabled': disabled }">
    <el-radio-group
      v-if="question.type === 'single_choice' || question.type === 'true_false'"
      v-model="innerValue"
      :disabled="disabled"
      @change="handleChange"
    >
      <el-radio
        v-for="(option, idx) in parsedOptions"
        :key="idx"
        :value="getOptionValue(option)"
        :disabled="disabled"
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
      :disabled="disabled"
      @change="handleChange"
    >
      <el-checkbox
        v-for="(option, idx) in parsedOptions"
        :key="idx"
        :value="getOptionValue(option)"
        :disabled="disabled"
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
  disabled: {
    type: Boolean,
    default: false,
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
    if (option.key !== undefined) return String(option.key)
    if (option.value !== undefined) return String(option.value)
    if (option.label !== undefined) return String(option.label)
    if (option.id !== undefined) return String(option.id)
    return ''
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
  padding: 14px 16px;
  border: 1.5px solid #e4e7ed;
  border-radius: 10px;
  transition: all 0.2s;
  cursor: pointer;
  min-height: 44px;
}

.choice-option:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.choice-option :deep(.el-radio__input),
.choice-option :deep(.el-checkbox__input) {
  margin-right: 12px;
}

.choice-option :deep(.el-radio__input .el-radio__inner),
.choice-option :deep(.el-checkbox__input .el-checkbox__inner) {
  width: 18px;
  height: 18px;
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

.choice-option:has(.el-radio__input.is-checked),
.choice-option:has(.el-checkbox__input.is-checked) {
  border-color: #409eff;
  background: #ecf5ff;
}

.option-label {
  font-weight: 600;
  margin-right: 6px;
  color: #303133;
  font-size: 15px;
}

.option-content {
  color: #606266;
  line-height: 1.6;
  font-size: 14px;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .choice-question {
    gap: 10px;
  }

  .choice-option {
    padding: 14px 14px;
    border-radius: 10px;
  }

  .choice-option :deep(.el-radio__input),
  .choice-option :deep(.el-checkbox__input) {
    margin-right: 10px;
  }

  .option-label {
    font-size: 15px;
  }

  .option-content {
    font-size: 14px;
    line-height: 1.55;
  }
}

@media (max-width: 380px) {
  .choice-option {
    padding: 12px;
  }

  .option-label {
    font-size: 14px;
  }

  .option-content {
    font-size: 13px;
  }
}
</style>
