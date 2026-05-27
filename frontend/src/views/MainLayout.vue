<template>
  <div class="main-layout">
    <header class="top-nav">
      <div class="nav-left">
        <router-link :to="homeLink" class="logo">AI 教学助手</router-link>
      </div>
      <div class="nav-right">
        <template v-if="effectiveRole === 'admin'">
          <router-link to="/admin/dashboard" class="nav-link">控制台</router-link>
          <router-link to="/admin/teachers" class="nav-link">教师管理</router-link>
          <router-link to="/admin/majors" class="nav-link">专业管理</router-link>
          <router-link to="/admin/dify-config" class="nav-link">Dify 配置</router-link>
        </template>
        <template v-else-if="effectiveRole === 'teacher'">
          <router-link to="/teacher/dashboard" class="nav-link">仪表盘</router-link>
          <router-link to="/teacher/classes" class="nav-link">班级管理</router-link>
          <router-link to="/teacher/settings" class="nav-link">系统配置</router-link>
        </template>
        <span class="user-info">{{ userName }}</span>
        <button @click="handleLogout" class="btn-text">退出</button>
      </div>
    </header>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const userName = computed(() => userStore.user?.display_name || userStore.user?.username || localStorage.getItem('user_name') || '用户')
// 优先用 store 里的角色；store 还没回填（首屏刷新瞬间）时用 localStorage 兜底，避免菜单闪没。
const effectiveRole = computed(() => userStore.role || localStorage.getItem('user_role') || '')
const homeLink = computed(() => {
  if (effectiveRole.value === 'admin') return '/admin/dashboard'
  if (effectiveRole.value === 'teacher') return '/teacher/dashboard'
  return '/chat'
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

