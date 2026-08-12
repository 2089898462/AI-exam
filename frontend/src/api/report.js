import request from '@/utils/request'

export const reportApi = {
  // 生成报告
  generate: (data) => request.post('/reports/generate', data),
  
  // 根据考试记录获取报告
  getByExamRecord: (examRecordId) => request.get(`/reports/exam-records/${examRecordId}`),
  
  // 获取报告详情
  getDetail: (reportId) => request.get(`/reports/${reportId}`),
  
  // 获取报告列表
  getList: (params) => request.get('/reports', { params }),
  
  // 删除报告
  delete: (reportId) => request.delete(`/reports/${reportId}`),
}
