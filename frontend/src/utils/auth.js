const TOKEN_KEY = 'exam_token'

export const auth = {
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },
  getToken() {
    return localStorage.getItem(TOKEN_KEY) || null
  },
  removeToken() {
    localStorage.removeItem(TOKEN_KEY)
  },
}
