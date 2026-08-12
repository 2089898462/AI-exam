import { createRouter, createWebHistory } from 'vue-router'
import { setupRouterGuard } from './guard'

const routes = [
  {
    path: '/',
    redirect: '/candidate',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/candidate',
    name: 'CandidateEntry',
    component: () => import('@/views/candidate/CandidateEntry.vue'),
    meta: { title: '考生入口' },
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
      {
        path: 'templates',
        name: 'TemplateList',
        component: () => import('@/views/admin/template/TemplateList.vue'),
        meta: { title: '试卷模板' },
      },
      {
        path: 'templates/create',
        name: 'TemplateCreate',
        component: () => import('@/views/admin/template/TemplateCreate.vue'),
        meta: { title: '创建模板' },
      },
      {
        path: 'templates/:id/edit',
        name: 'TemplateEdit',
        component: () => import('@/views/admin/template/TemplateCreate.vue'),
        meta: { title: '编辑模板' },
      },
      {
        path: 'templates/:id',
        name: 'TemplateDetail',
        component: () => import('@/views/admin/template/TemplateDetail.vue'),
        meta: { title: '模板详情' },
      },
      {
        path: 'grading',
        name: 'GradingResultList',
        component: () => import('@/views/admin/grading/GradingResultList.vue'),
        meta: { title: '评分结果' },
      },
      {
        path: 'grading/:examRecordId',
        name: 'GradingResultDetail',
        component: () => import('@/views/admin/grading/GradingResultDetail.vue'),
        meta: { title: '评分详情' },
      },
      {
        path: 'reports',
        name: 'ReportList',
        component: () => import('@/views/admin/report/ReportList.vue'),
        meta: { title: 'AI 分析报告' },
      },
      {
        path: 'reports/:id',
        name: 'ReportDetail',
        component: () => import('@/views/admin/report/ReportDetail.vue'),
        meta: { title: '报告详情' },
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