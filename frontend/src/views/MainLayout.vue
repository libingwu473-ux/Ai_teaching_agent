<template>
  <div :class="['main-layout', { 'is-chat': isStudentChat }]">
    <!-- 侧边栏：仅后台页面 -->
    <aside v-if="!isStudentChat" :class="['sidebar', { 'is-collapsed': collapsed }]">
      <div class="sidebar-logo">
        <span class="logo-dot">AI</span>
        <span v-if="!collapsed" class="sidebar-logo-text">教学助手</span>
      </div>
      <nav class="sidebar-nav">
        <template v-if="effectiveRole === 'admin'">
          <div class="sidebar-section-label">管理</div>
          <router-link
            v-for="item in adminMenu" :key="item.path"
            :to="item.path"
            :class="['sidebar-link', { 'is-active': isActive(item.path) }]"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span class="sidebar-link-text">{{ item.label }}</span>
          </router-link>
        </template>
        <template v-else-if="effectiveRole === 'teacher'">
          <div class="sidebar-section-label">教学</div>
          <router-link
            v-for="item in teacherMenu" :key="item.path"
            :to="item.path"
            :class="['sidebar-link', { 'is-active': isActive(item.path) }]"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span class="sidebar-link-text">{{ item.label }}</span>
          </router-link>
        </template>
      </nav>
    </aside>

    <!-- 内容区 -->
    <div class="main-area">
      <header v-if="!isStudentChat" class="top-nav">
        <div class="top-nav-left">
          <button class="top-nav-collapse-btn" @click="collapsed = !collapsed" title="折叠/展开侧边栏">
            <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </button>
          <span class="top-nav-title">{{ currentPageTitle }}</span>
        </div>
        <div class="top-nav-right">
          <el-dropdown trigger="click">
            <div class="top-nav-user">
              <div class="top-nav-avatar">{{ avatarText }}</div>
              <span>{{ userName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="User" disabled>
                  {{ userName }}（{{ roleLabel }}）
                </el-dropdown-item>
                <el-dropdown-item divided :icon="SwitchButton" @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <!-- 学生聊天页：用一个简化顶栏（保留退出按钮） -->
      <header v-else class="top-nav">
        <div class="top-nav-left">
          <span class="logo-dot" style="width: 28px; height: 28px; border-radius: 8px; background: linear-gradient(135deg, var(--brand-400), var(--brand-600)); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;">AI</span>
          <span style="font-weight: 600; color: var(--gray-900); font-size: 15px;">教学助手</span>
        </div>
        <div class="top-nav-right">
          <el-dropdown trigger="click">
            <div class="top-nav-user">
              <div class="top-nav-avatar">{{ avatarText }}</div>
              <span>{{ userName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="SwitchButton" @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, markRaw, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import {
  Odometer, User, School, Reading, Setting, DataAnalysis,
  UserFilled, Connection, Fold, Expand, ArrowDown, SwitchButton,
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const collapsed = ref(false)

const userName = computed(() => userStore.user?.display_name || userStore.user?.username || localStorage.getItem('user_name') || '用户')
const avatarText = computed(() => (userName.value || '?').slice(0, 1))
const effectiveRole = computed(() => userStore.role || localStorage.getItem('user_role') || '')
const isStudentChat = computed(() => effectiveRole.value === 'student')
const roleLabel = computed(() => ({ admin: '管理员', teacher: '教师', student: '学生' })[effectiveRole.value] || '')

const adminMenu = [
  { path: '/admin/dashboard', label: '控制台', icon: markRaw(Odometer) },
  { path: '/admin/teachers',  label: '教师管理', icon: markRaw(UserFilled) },
  { path: '/admin/majors',    label: '专业管理', icon: markRaw(Reading) },
  { path: '/admin/dify-config', label: 'Dify 配置', icon: markRaw(Connection) },
]
const teacherMenu = [
  { path: '/teacher/dashboard', label: '仪表盘', icon: markRaw(DataAnalysis) },
  { path: '/teacher/classes',   label: '班级管理', icon: markRaw(School) },
  { path: '/teacher/settings',  label: '评分设置', icon: markRaw(Setting) },
]

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

const currentPageTitle = computed(() => {
  const menu = effectiveRole.value === 'admin' ? adminMenu :
               effectiveRole.value === 'teacher' ? teacherMenu : []
  const hit = menu.find((m) => isActive(m.path))
  if (hit) return hit.label
  // 二级页面提示
  if (route.path.startsWith('/teacher/classes/')) return '班级 / 学生'
  if (route.path.startsWith('/teacher/students/')) return '学生详情'
  if (route.path.startsWith('/teacher/scores/')) return '评分复核'
  return ''
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>
