import request from '@/utils/request'

export const templateApi = {
  getTemplateList: (params) => request.get('/templates', { params }),
  getTemplateDetail: (id) => request.get(`/templates/${id}`),
  createTemplate: (data) => request.post('/templates', data),
  updateTemplate: (id, data) => request.put(`/templates/${id}`, data),
  deleteTemplate: (id) => request.delete(`/templates/${id}`),
  activateTemplate: (id) => request.post(`/templates/${id}/activate`),
  deactivateTemplate: (id) => request.post(`/templates/${id}/deactivate`),
  
  getTemplateQuestions: (templateId) => request.get(`/templates/${templateId}/questions`),
  createTemplateQuestion: (templateId, data) => request.post(`/templates/${templateId}/questions`, data),
  batchCreateQuestions: (templateId, data) => request.post(`/templates/${templateId}/questions/batch`, data),
  updateTemplateQuestion: (templateId, questionId, data) => request.put(`/templates/${templateId}/questions/${questionId}`, data),
  deleteTemplateQuestion: (templateId, questionId) => request.delete(`/templates/${templateId}/questions/${questionId}`),
  deleteAllTemplateQuestions: (templateId) => request.delete(`/templates/${templateId}/questions`),
  importQuestionsToTemplate: (templateId, data) => request.post(`/templates/${templateId}/questions/import`, data),
  
  createExamFromTemplate: (templateId, data) => request.post(`/templates/${templateId}/create-exam`, data),
}
