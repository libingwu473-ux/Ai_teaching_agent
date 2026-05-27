import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import { useUserStore } from './stores/user'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 启动时如果已登录（有 token），恢复用户信息到 store。
// 否则刷新页面后 store 是空的，MainLayout 的角色判断会失败、导航条会消失。
const userStore = useUserStore()
if (localStorage.getItem('access_token')) {
  userStore.fetchProfile()
}

app.mount('#app')
