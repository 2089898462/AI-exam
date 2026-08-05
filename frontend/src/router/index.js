import { createRouter, createWebHistory } from 'vue-router'
import { setupRouterGuard } from './guard'

const routes = [
  {
    path: '/',
    redirect: '/admin/exams',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/admin/exams',
    children: [
      {
        path: 'exams',
        name: 'ExamList',
        component: () => import('@/views/admin/exam/ExamList.vue'),
        meta: { title: '考试管理' },
      },
      {
        path: 'exams/create',
        name: 'ExamCreate',
        component: () => import('@/views/admin/exam/ExamCreate.vue'),
        meta: { title: '创建考试' },
      },
      {
        path: 'exams/:id/edit',
        name: 'ExamEdit',
        component: () => import('@/views/admin/exam/ExamCreate.vue'),
        meta: { title: '编辑考试' },
      },
      {
        path: 'exams/:id',
        name: 'ExamDetail',
        component: () => import('@/views/admin/exam/ExamDetail.vue'),
        meta: { title: '考试详情' },
      },
    ],
  },
  {
    path: '/exam/:id',
    name: 'ExamEntry',
    component: () => import('@/views/exam/Entry.vue'),
    meta: { title: '参加考试' },
  },
  {
    path: '/exam/record/:id',
    name: 'ExamTaking',
    component: () => import('@/views/exam/Exam.vue'),
    meta: { title: '考试进行中' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

setupRouterGuard(router)

export default router