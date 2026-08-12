import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import { auth } from '@/utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null,
    token: auth.getToken(),
  }),
  getters: {
    isLoggedIn() {
      return !!this.token
    },
    username() {
      return this.userInfo?.username || ''
    },
    displayName() {
      return this.userInfo?.display_name || this.userInfo?.username || ''
    },
    role() {
      return this.userInfo?.role || ''
    },
  },
  actions: {
    async login(credentials) {
      const res = await authApi.login(credentials)
      const token = res.data.access_token
      const role = res.data.user?.role || ''
      auth.setToken(token)
      auth.setRole(role)
      this.token = token
      await this.getUserInfo()
      return res
    },
    async getUserInfo() {
      const res = await authApi.getCurrentUser()
      this.userInfo = res.data
      return res
    },
    logout() {
      auth.removeToken()
      this.token = null
      this.userInfo = null
    },
    hasRole(role) {
      return this.role === role
    },
    isAdminOrHR() {
      return this.role === 'admin' || this.role === 'hr'
    },
  },
})
