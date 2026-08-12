import request from '@/utils/request'

export const examApi = {
  getExamList: (params) => request.get('/exams', { params }),
  getExamDetail: (id) => request.get(`/exams/${id}`),
  createExam: (data) => request.post('/exams', data),
  updateExam: (id, data) => request.put(`/exams/${id}`, data),
  deleteExam: (id) => request.delete(`/exams/${id}`),
  publishExam: (id) => request.post(`/exams/${id}/publish`),
  closeExam: (id) => request.post(`/exams/${id}/close`),
  cloneExam: (id, newTitle) => {
    const params = newTitle ? { new_title: newTitle } : {}
    return request.post(`/exams/${id}/clone`, { params })
  },
  importExam: (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/exams/${id}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importJson: (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/exams/${id}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (params) => request.get('/exams', { params }),
  get: (id) => request.get(`/exams/${id}`),
  create: (data) => request.post('/exams', data),
  update: (id, data) => request.put(`/exams/${id}`, data),
  delete: (id) => request.delete(`/exams/${id}`),
  publish: (id) => request.post(`/exams/${id}/publish`),
  close: (id) => request.post(`/exams/${id}/close`),
}

export { questionApi } from './question'
