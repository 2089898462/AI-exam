const TOKEN_KEY = 'exam_token'
const USER_ROLE_KEY = 'exam_user_role'

export const auth = {
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },
  getToken() {
    return localStorage.getItem(TOKEN_KEY) || null
  },
  setRole(role) {
    localStorage.setItem(USER_ROLE_KEY, role)
  },
  getRole() {
    return localStorage.getItem(USER_ROLE_KEY) || null
  },
  removeToken() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_ROLE_KEY)
  },
}
