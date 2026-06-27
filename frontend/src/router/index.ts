import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('@/views/auth/Signup.vue'),
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/projects/ProjectList.vue'),
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectDetail',
    component: () => import('@/views/projects/ProjectDetail.vue'),
  },
  {
    path: '/projects/:projectId/analyses/:analysisId',
    name: 'AnalysisDetail',
    component: () => import('@/views/analysis/AnalysisDetail.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
