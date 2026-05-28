<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>AI 教学助手</h1>
      <h2>登录到你的账号</h2>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            autofocus
          >
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon style="margin-bottom: 14px;" />
        <el-button
          type="primary"
          size="large"
          style="width: 100%;"
          :loading="loading"
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登录' }}
        </el-button>
      </el-form>
      <p class="auth-hint">管理员账号请联系系统超级管理员开通</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api/auth'
import { useUserStore } from '../stores/user'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()

const formRef = ref(null)
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  error.value = ''
  try {
    const resp = await login(form.value)
    const data = resp.data
    chatStore.reset()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    userStore.setUser(data)
    router.push(
      data.role === 'teacher' ? '/teacher/dashboard'
      : data.role === 'admin' ? '/admin/dashboard'
      : '/chat'
    )
  } catch (e) {
    error.value = e.response?.data?.error || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-hint {
  text-align: center;
  margin-top: 18px;
  font-size: 12px;
  color: var(--gray-400);
}
</style>
