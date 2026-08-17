import request from '@/utils/request'

export const gradingResultApi = {
  getResults: (params) => request.get('/grading/results', { params }),
  getResultDetail: (examRecordId) => request.get(`/grading/results/${examRecordId}`),
  updateHRReview: (examRecordId, data) => request.put(`/grading/results/${examRecordId}/review`, data),
}
