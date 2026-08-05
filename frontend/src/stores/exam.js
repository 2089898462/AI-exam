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
