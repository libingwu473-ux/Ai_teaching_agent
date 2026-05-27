import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getProfile } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const isLoggedIn = computed(() => !!user.value)
  const role = computed(() => user.value?.role || '')
  const isStudent = computed(() => role.value === 'student')
  const isTeacher = computed(() => role.value === 'teacher')
  const isAdmin = computed(() => role.value === 'admin')
  // 兼容旧代码：以前 isTeacher 同时覆盖 admin
  const isTeacherOrAdmin = computed(() => isTeacher.value || isAdmin.value)

  function setUser(data) {
    user.value = data
    if (data) {
      localStorage.setItem('user_role', data.role)
      localStorage.setItem('user_name', data.display_name || data.username)
    }
  }

  async function fetchProfile() {
    try {
      const resp = await getProfile()
      setUser(resp.data)
    } catch {
      user.value = null
    }
  }

  function logout() {
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_name')
    // 清理对话相关的内存状态，避免下个登录的用户看到上一个用户的数据
    import('./chat').then(({ useChatStore }) => useChatStore().reset())
  }

  return { user, isLoggedIn, role, isStudent, isTeacher, isAdmin, isTeacherOrAdmin, setUser, fetchProfile, logout }
})
