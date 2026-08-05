/**
 * 自动保存 Hook
 * 实现答案变更监听 + 防抖保存 + 保存状态更新
 * 
 * 特性：
 * - 防抖保存：答案变更后延迟保存，避免频繁请求
 * - 脏标记：只在真实变更时触发保存
 * - 保存状态：saving / saved / error
 * - 手动保存：支持立即保存所有答案
 * 
 * 使用：
 *   const { saveCurrentAnswer, saveAllAnswers, retrySave } = useAutoSave(examStore)
 */
import { ref, watch, onBeforeUnmount } from 'vue'

const DEBOUNCE_DELAY = 1500 // 防抖延迟 1.5 秒

export function useAutoSave(examStore, options = {}) {
  const debounceDelay = options.debounceDelay || DEBOUNCE_DELAY
  
  let debounceTimer = null
  let pendingQuestionId = null
  let isSavingInternally = false

  /**
   * 防抖保存单个答案
   */
  function debouncedSave() {
    if (isSavingInternally || !pendingQuestionId) return
    
    const questionId = pendingQuestionId
    pendingQuestionId = null
    
    const answerContent = examStore.answers[questionId]
    if (answerContent === undefined || answerContent === null || answerContent === '') {
      // 空答案不保存
      examStore.markClean()
      return
    }
    
    isSavingInternally = true
    examStore.saveAnswerToServer(questionId, answerContent).finally(() => {
      isSavingInternally = false
      // 如果有新的变更等待保存
      if (pendingQuestionId) {
        scheduleSave()
      }
    })
  }

  /**
   * 调度防抖保存
   */
  function scheduleSave() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      debouncedSave()
    }, debounceDelay)
  }

  /**
   * 保存当前题目答案（触发防抖）
   */
  function saveCurrentAnswer(questionId, value) {
    // 更新 store
    examStore.setAnswer(questionId, value)
    
    // 设置脏标记
    examStore.isDirty = true
    
    // 调度防抖保存
    pendingQuestionId = questionId
    scheduleSave()
  }

  /**
   * 立即保存单个答案（不防抖）
   */
  async function saveAnswerNow(questionId) {
    const answerContent = examStore.answers[questionId]
    if (answerContent === undefined || answerContent === null || answerContent === '') {
      return true
    }
    return await examStore.saveAnswerToServer(questionId, answerContent)
  }

  /**
   * 保存所有答案
   */
  async function saveAllAnswers() {
    // 取消待执行的防抖保存
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
      pendingQuestionId = null
    }
    
    // 收集所有答案
    const answersToSave = []
    for (const [questionId, answerContent] of Object.entries(examStore.answers)) {
      if (answerContent !== undefined && answerContent !== null && answerContent !== '' &&
          !(Array.isArray(answerContent) && answerContent.length === 0)) {
        answersToSave.push({
          questionId: parseInt(questionId),
          answerContent,
        })
      }
    }
    
    if (answersToSave.length === 0) return true
    
    return await examStore.saveAllAnswersToServer(answersToSave)
  }

  /**
   * 重试保存（保存失败后）
   */
  function retrySave() {
    if (!examStore.saveError) return
    examStore.markClean()
    return saveAllAnswers()
  }

  /**
   * 立即保存当前题并取消防抖
   * 用于切换题目前保存
   */
  async function flushSave() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    
    if (pendingQuestionId) {
      const questionId = pendingQuestionId
      pendingQuestionId = null
      const answerContent = examStore.answers[questionId]
      if (answerContent !== undefined && answerContent !== null && answerContent !== '') {
        return await examStore.saveAnswerToServer(questionId, answerContent)
      }
    }
    return true
  }

  /**
   * 清理定时器
   */
  function cleanup() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    pendingQuestionId = null
  }

  // 组件卸载时清理
  onBeforeUnmount(() => {
    cleanup()
  })

  return {
    saveCurrentAnswer,
    saveAnswerNow,
    saveAllAnswers,
    retrySave,
    flushSave,
    cleanup,
  }
}
