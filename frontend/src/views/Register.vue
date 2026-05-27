<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>AI 教学助手</h1>
      <h2>用户注册</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" required placeholder="请输入用户名" />
        </div>
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="form.email" type="email" required placeholder="请输入邮箱" />
        </div>
        <div class="form-group">
          <label>显示名称</label>
          <input v-model="form.display_name" type="text" placeholder="请输入显示名称" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" required placeholder="至少6位密码" />
        </div>
        <div class="form-group">
          <label>角色</label>
          <select v-model="form.role">
            <option value="student">学生</option>
            <option value="teacher">教师</option>
          </select>
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p class="link-text">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api/auth'
import { useUserStore } from '../stores/user'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()

const form = ref({
  username: '',
  email: '',
  display_name: '',
  password: '',
  role: 'student',
})
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  loading.value = true
  error.value = ''
  try {
    const resp = await register(form.value)
    const data = resp.data
    chatStore.reset()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    userStore.setUser(data)
    router.push(data.role === 'teacher' ? '/teacher/dashboard' : '/chat')
  } catch (e) {
    const errData = e.response?.data
    if (errData) {
      const msgs = []
      for (const key in errData) {
        msgs.push(...(Array.isArray(errData[key]) ? errData[key] : [errData[key]]))
      }
      error.value = msgs.join('; ') || '注册失败'
    } else {
      error.value = '注册失败，请重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
