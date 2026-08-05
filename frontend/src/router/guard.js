import { auth } from '@/utils/auth'

const WHITE_LIST = ['/login']

export function setupRouterGuard(router) {
  router.beforeEach((to, from, next) => {
    const token = auth.getToken()

    if (token) {
      if (to.path === '/login') {
        next('/admin/exams')
      } else {
        next()
      }
    } else {
      if (to.path.startsWith('/admin')) {
        next('/login')
      } else {
        next()
      }
    }
  })
}
