import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
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
      // 教师端
      {
        path: 'teacher/dashboard',
        name: 'TeacherDashboard',
        component: () => import('../views/teacher/Dashboard.vue'),
        meta: { role: 'teacher' },
      },
      {
        path: 'teacher/classes',
        name: 'TeacherClasses',
        component: () => import('../views/teacher/ClassManage.vue'),
        meta: { role: 'teacher' },
      },
      {
        path: 'teacher/classes/:id/students',
        name: 'TeacherClassStudents',
        component: () => import('../views/teacher/ClassStudents.vue'),
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
      // 管理员端
      {
        path: 'admin/dashboard',
        name: 'AdminDashboard',
        component: () => import('../views/admin/Dashboard.vue'),
        meta: { role: 'admin' },
      },
      {
        path: 'admin/teachers',
        name: 'AdminTeachers',
        component: () => import('../views/admin/TeacherManage.vue'),
        meta: { role: 'admin' },
      },
      {
        path: 'admin/majors',
        name: 'AdminMajors',
        component: () => import('../views/admin/MajorManage.vue'),
        meta: { role: 'admin' },
      },
      {
        path: 'admin/dify-config',
        name: 'AdminDifyConfig',
        component: () => import('../views/admin/DifyConfig.vue'),
        meta: { role: 'admin' },
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
  if (to.meta.role) {
    // teacher 路由：teacher 自己进；admin 也允许穿透（只读为主）
    if (to.meta.role === 'teacher' && userRole !== 'teacher' && userRole !== 'admin') {
      return next(userRole === 'student' ? '/chat' : '/login')
    }
    // admin 路由：仅 admin
    if (to.meta.role === 'admin' && userRole !== 'admin') {
      return next(userRole === 'teacher' ? '/teacher/dashboard' : '/chat')
    }
    // student 路由：仅 student（teacher/admin 进了对话页没意义，但保留权限上来说可让 teacher/admin 偷看）
    if (to.meta.role === 'student' && userRole !== 'student') {
      return next(userRole === 'admin' ? '/admin/dashboard' : '/teacher/dashboard')
    }
  }

  next()
})

export default router
