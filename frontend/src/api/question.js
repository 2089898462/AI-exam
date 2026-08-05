import request from '@/utils/request'

export const questionApi = {
  getQuestions: (examId) => request.get(`/exams/${examId}/questions`),
  createQuestion: (examId, data) => request.post('/questions', data, { params: { exam_id: examId } }),
  deleteQuestion: (id, examId) => request.delete(`/questions/${id}`, { params: { exam_id: examId } }),

  listByExam: (examId) => request.get(`/exams/${examId}/questions`),
  create: (examId, data) => request.post('/questions', data, { params: { exam_id: examId } }),
  delete: (id, examId) => request.delete(`/questions/${id}`, { params: { exam_id: examId } }),
}
