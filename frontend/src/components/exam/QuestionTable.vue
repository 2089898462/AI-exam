<template>
  <div class="question-table">
    <el-table v-loading="loading" :data="questions" border stripe>
      <el-table-column label="#" type="index" width="60" />
      <el-table-column prop="question_no" label="题号" width="80" />
      <el-table-column label="题型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ questionTypeText(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="100">
        <template #default="{ row }">
          {{ row.category || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="content" label="题目内容" min-width="300" show-overflow-tooltip />
      <el-table-column prop="score" label="分数" width="80" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            size="small"
            type="danger"
            link
            :disabled="readonly"
            @click="handleDelete(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!questions.length && !loading" description="暂无题目" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { questionApi } from '@/api'

const props = defineProps({
  examId: { type: [Number, String], default: null },
  questions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['delete'])

const localQuestions = ref([...props.questions])

watch(
  () => props.questions,
  (val) => {
    localQuestions.value = [...val]
  },
  { immediate: true, deep: true }
)

const questionTypeText = (type) => ({
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '问答题',
})[type] || type

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除题目「${row.content?.slice(0, 30)}${row.content && row.content.length > 30 ? '...' : ''}」吗？`, '删除确认', {
      type: 'warning',
    })
    await questionApi.deleteQuestion(row.id, props.examId)
    ElMessage.success('删除成功')
    emit('delete', row)
  } catch (e) {
    /* cancelled or error from interceptor */
  }
}
</script>

<style scoped>
.question-table {
  width: 100%;
}
</style>
