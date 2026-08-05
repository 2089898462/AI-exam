<template>
  <div class="question-card" :class="{ 'question-card--disabled': disabled }">
    <div class="question-header">
      <span class="question-no">{{ questionNo }}</span>
      <el-tag :type="typeTagType" size="small" class="question-type">
        {{ typeLabel }}
      </el-tag>
      <span class="question-score">{{ question.score }} 分</span>
      <el-tag v-if="disabled" type="info" size="small" class="readonly-tag">已提交</el-tag>
    </div>
    <div class="question-content">
      <span v-html="question.content"></span>
    </div>
    <div class="question-body">
      <ChoiceQuestion
        v-if="isChoice"
        :question="question"
        :model-value="currentAnswer"
        :disabled="disabled"
        @update:model-value="handleAnswer"
      />
      <TextQuestion
        v-else
        :question="question"
        :model-value="currentAnswer"
        :disabled="disabled"
        @update:model-value="handleAnswer"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ChoiceQuestion from './ChoiceQuestion.vue'
import TextQuestion from './TextQuestion.vue'

const props = defineProps({
  question: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    default: 0,
  },
  answer: {
    type: [String, Array],
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:answer'])

const questionNo = computed(() => {
  return props.question.question_no || `第 ${props.index + 1} 题`
})

const typeLabel = computed(() => {
  const map = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    short_answer: '简答题',
  }
  return map[props.question.type] || props.question.type
})

const typeTagType = computed(() => {
  const map = {
    single_choice: '',
    multiple_choice: 'success',
    true_false: 'warning',
    short_answer: 'info',
  }
  return map[props.question.type] || ''
})

const isChoice = computed(() => {
  return ['single_choice', 'multiple_choice', 'true_false'].includes(
    props.question.type
  )
})

const currentAnswer = computed({
  get() {
    return props.answer
  },
  set(val) {
    if (!props.disabled) {
      emit('update:answer', val)
    }
  },
})

function handleAnswer(val) {
  if (!props.disabled) {
    emit('update:answer', val)
  }
}
</script>

<style scoped>
.question-card--disabled {
  opacity: 0.85;
  pointer-events: none;
}

.question-card--disabled .question-body {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 12px;
}

.readonly-tag {
  margin-left: auto;
}

.question-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.question-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.question-no {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.question-type {
  font-size: 12px;
}

.question-score {
  margin-left: auto;
  font-size: 13px;
  color: #909399;
}

.question-content {
  font-size: 15px;
  color: #303133;
  line-height: 1.8;
  margin-bottom: 20px;
}

.question-body {
  min-height: 100px;
}
</style>
