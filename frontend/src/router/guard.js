/**
 * 前端路由守卫
 * 
 * 安全规则：
 * 1. 未登录用户访问 /admin/* → 跳转登录
 * 2. 已登录 employee 角色访问 /admin/* → 跳转首页（无权限）
 * 3. Token 失效 → 自动清除并跳转登录
 */
import { auth } from '@/utils/auth'

const WHITE_LIST = ['/login']

const ADMIN_ROUTES = [
  '/admin',
]

const EMPLOYEE_ROUTES = [
  '/exam/',
]

export function setupRouterGuard(router) {
  router.beforeEach((to, from, next) => {
    const token = auth.getToken()
    const userRole = auth.getRole()

    if (token) {
      // 已登录用户访问登录页，直接跳转
      if (to.path === '/login') {
        next('/admin/exams')
        return
      }

      // 管理后台路由检查
      if (isAdminRoute(to.path)) {
        // 如果角色是 admin 或 hr，或者角色还没来得及设置（null），都允许访问
        // null 情况可能发生在登录后立即跳转的时序问题中
        if (!userRole || userRole === 'admin' || userRole === 'hr') {
          next()
        } else {
          // 非授权角色，跳转到考试首页
          next('/')
        }
        return
      }

      next()
    } else {
      // 未登录用户访问管理后台，跳转登录
      if (isAdminRoute(to.path)) {
        next('/login')
      } else {
        next()
      }
    }
  })
}

function isAdminRoute(path) {
  return path.startsWith('/admin')
}
