<template>
  <div class="main-layout">
    <header class="top-nav">
      <div class="nav-left">
        <router-link to="/chat" class="logo">AI 教学助手</router-link>
      </div>
      <div class="nav-right">
        <template v-if="userStore.isTeacher">
          <router-link to="/teacher/dashboard" class="nav-link">仪表盘</router-link>
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

const userName = computed(() => localStorage.getItem('user_name') || '用户')

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>
