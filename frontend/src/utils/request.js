import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { auth } from '@/utils/auth'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use(
  (config) => {
    const token = auth.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 200 || res.code === 201) {
      return res
    }
    const errorMessages = {
      400: res.message || '请求参数错误',
      401: res.message || '未登录或登录已过期',
      403: res.message || '没有操作权限',
      404: res.message || '资源不存在',
      422: res.message || '数据校验失败',
      500: res.message || '服务器内部错误',
    }
    const msg = errorMessages[res.code] || res.message || '未知错误'
    ElMessage.error(msg)
    if (res.code === 401) {
      auth.removeToken()
      router.push('/login')
    }
    if (res.code === 403) {
      router.push('/exam')
    }
    return Promise.reject(new Error(msg))
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      const msg = data?.message || `请求失败 (${status})`
      if (status === 401) {
        auth.removeToken()
        router.push('/login')
        return Promise.reject(error)
      }
      if (status === 403) {
        ElMessage.error(msg)
        router.push('/exam')
        return Promise.reject(error)
      }
      // 404 错误静默处理，不弹窗（交由组件自行处理）
      if (status === 404) {
        console.warn(`[404] ${error.config?.url}: ${msg}`)
        return Promise.reject(error)
      }
      if (status !== 422) {
        ElMessage.error(msg)
      }
    } else if (error.message.includes('timeout')) {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络连接异常')
    }
    return Promise.reject(error)
  }
)

export default request
