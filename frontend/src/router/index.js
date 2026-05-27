import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
  },
  {
    path: '/',
    component: () => import('../views/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/chat' },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/ChatView.vue'),
        meta: { role: 'student' },
      },
      {
        path: 'chat/:sessionId',
        name: 'ChatSession',
        component: () => import('../views/ChatView.vue'),
        meta: { role: 'student' },
      },
      {
        path: 'teacher/dashboard',
        name: 'TeacherDashboard',
        component: () => import('../views/teacher/Dashboard.vue'),
        meta: { role: 'teacher' },
      },
      {
        path: 'teacher/students/:id',
        name: 'StudentDetail',
        component: () => import('../views/teacher/StudentDetail.vue'),
        meta: { role: 'teacher' },
      },
      {
        path: 'teacher/scores/:id',
        name: 'ScoreReview',
        component: () => import('../views/teacher/ScoreReview.vue'),
        meta: { role: 'teacher' },
      },
      {
        path: 'teacher/settings',
        name: 'TeacherSettings',
        component: () => import('../views/teacher/Settings.vue'),
        meta: { role: 'teacher' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }

  const userRole = localStorage.getItem('user_role')
  if (to.meta.role === 'teacher' && userRole !== 'teacher' && userRole !== 'admin') {
    return next('/chat')
  }

  next()
})

export default router
