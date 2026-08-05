import { defineStore } from 'pinia'
import { examRecordApi } from '@/api/examRecord'

export const useExamStore = defineStore('exam', {
  state: () => ({
    examId: null,
    recordId: null,
    candidateName: '',
    candidatePhone: '',
    candidateEmail: '',
    status: '',
    examInfo: null,
    questions: [],
    answers: {},
    // 保存状态管理
    isSaving: false,
    lastSavedAt: null,
    saveError: null,
    isDirty: false,
  }),
  getters: {
    hasRecord() {
      return !!this.recordId
    },
    isStarted() {
      return this.status === 'in_progress'
    },
    answeredCount() {
      return Object.values(this.answers).filter(
        (v) => v !== null && v !== undefined && v !== '' &&
               !(Array.isArray(v) && v.length === 0)
      ).length
    },
    totalQuestions() {
      return this.questions.length
    },
    hasUnsavedChanges() {
      return this.isDirty && !this.isSaving
    },
    saveStatus() {
      if (this.isSaving) return 'saving'
      if (this.saveError) return 'error'
      if (this.lastSavedAt) return 'saved'
      return 'idle'
    },
    saveStatusText() {
      const map = {
        idle: '',
        saving: '保存中...',
        saved: '已保存',
        error: '保存失败，点击重试',
      }
      return map[this.saveStatus]
    },
  },
  actions: {
    setExamInfo(examId) {
      this.examId = examId
      this.clearRecord()
    },
    clearRecord() {
      this.recordId = null
      this.candidateName = ''
      this.candidatePhone = ''
      this.candidateEmail = ''
      this.status = ''
      this.examInfo = null
      this.questions = []
      this.answers = {}
    },
    async createRecord(payload) {
      const res = await examRecordApi.createRecord(payload)
      this.recordId = res.data.id
      this.examId = res.data.exam_id
      this.candidateName = res.data.candidate_name
      this.candidatePhone = res.data.candidate_phone || ''
      this.candidateEmail = res.data.candidate_email || ''
      this.status = res.data.status
      return res.data
    },
    async loadExamPaper(recordId) {
      const res = await examRecordApi.getExamPaper(recordId)
      this.recordId = res.data.record_id
      this.examId = res.data.exam_id
      this.candidateName = res.data.candidate_name
      this.status = res.data.status
      this.examInfo = {
        examId: res.data.exam_id,
        title: res.data.exam_title,
        description: res.data.exam_description,
        durationMinutes: res.data.duration_minutes,
        passScore: res.data.pass_score,
        questionCount: res.data.question_count,
      }
      this.questions = res.data.questions
      this._initAnswers()
      return res.data
    },
    _initAnswers() {
      const map = {}
      for (const q of this.questions) {
        if (q.type === 'multiple_choice') {
          map[q.id] = []
        } else {
          map[q.id] = ''
        }
      }
      this.answers = map
    },
    setAnswer(questionId, value) {
      this.answers[questionId] = value
      this.isDirty = true
    },
    markClean() {
      this.isDirty = false
      this.saveError = null
    },
    async saveAnswerToServer(questionId, answerContent) {
      this.isSaving = true
      this.saveError = null
      try {
        await examRecordApi.saveAnswer(this.recordId, {
          question_id: questionId,
          answer_content: Array.isArray(answerContent) ? answerContent.join(',') : answerContent,
        })
        this.isSaving = false
        this.lastSavedAt = new Date()
        this.isDirty = false
        return true
      } catch (err) {
        this.isSaving = false
        this.saveError = err.message || '保存失败'
        return false
      }
    },
    async saveAllAnswersToServer(answers) {
      this.isSaving = true
      this.saveError = null
      try {
        const answerList = answers.map(({ questionId, answerContent }) => ({
          question_id: questionId,
          answer_content: Array.isArray(answerContent) ? answerContent.join(',') : answerContent,
        }))
        await examRecordApi.saveAnswersBatch(this.recordId, { answers: answerList })
        this.isSaving = false
        this.lastSavedAt = new Date()
        this.isDirty = false
        return true
      } catch (err) {
        this.isSaving = false
        this.saveError = err.message || '保存失败'
        return false
      }
    },
    async startExam() {
      const res = await examRecordApi.startExam(this.recordId)
      this.status = res.data.status
      return res.data
    },
    async submitExam() {
      const res = await examRecordApi.submitExam(this.recordId)
      this.status = res.data.status
      return res.data
    },
  },
})
