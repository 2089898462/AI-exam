import request from '@/utils/request'

export const participantApi = {
  // 添加单个参与人员
  addParticipant: (examId, data) => {
    return request({
      url: `/exams/${examId}/participants`,
      method: 'post',
      data,
    })
  },

  // 批量添加参与人员
  addParticipantsBatch: (examId, participants) => {
    return request({
      url: `/exams/${examId}/participants/batch`,
      method: 'post',
      data: { participants },
    })
  },

  // 查询考试参与人员列表
  getParticipants: (examId, params = {}) => {
    return request({
      url: `/exams/${examId}/participants`,
      method: 'get',
      params,
    })
  },

  // 获取参与人员统计
  getParticipantCount: (examId) => {
    return request({
      url: `/exams/${examId}/participants/count`,
      method: 'get',
    })
  },

  // 查询单个参与人员
  getParticipant: (participantId) => {
    return request({
      url: `/participants/${participantId}`,
      method: 'get',
    })
  },

  // 删除参与人员
  removeParticipant: (participantId) => {
    return request({
      url: `/participants/${participantId}`,
      method: 'delete',
    })
  },

  // 更新参与人员状态
  updateParticipantStatus: (participantId, status) => {
    return request({
      url: `/participants/${participantId}/status`,
      method: 'put',
      data: { status },
    })
  },

  // 同步参与人员状态
  syncParticipantStatus: (examId) => {
    return request({
      url: `/exams/${examId}/participants/sync`,
      method: 'post',
    })
  },
}
