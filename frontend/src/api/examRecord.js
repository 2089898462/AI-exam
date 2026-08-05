import request from '@/utils/request'

export const examRecordApi = {
  getExamInfo: (examId) => request.get(`/exams/${examId}/info`),
  createRecord: (data) => request.post('/exam-records', data),
  getRecord: (id) => request.get(`/exam-records/${id}`),
  getExamPaper: (recordId) => request.get(`/exam-records/${recordId}/paper`),
  startExam: (id) => request.post(`/exam-records/${id}/start`),
  submitExam: (id) => request.post(`/exam-records/${id}/submit`),
  saveAnswer: (recordId, data) => request.post(`/exam-records/${recordId}/answers`, data),
  saveAnswersBatch: (recordId, data) => request.post(`/exam-records/${recordId}/answers/batch`, data),
  listRecords: (examId) => request.get(`/exams/${examId}/records`),
}
