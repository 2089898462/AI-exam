import request from '@/utils/request'

export const authApi = {
  login: (data) => request.post('/auth/login', data),
  getCurrentUser: () => request.get('/auth/me'),
}
