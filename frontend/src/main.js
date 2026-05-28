import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import './styles/theme.css'
import { useUserStore } from './stores/user'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 全局注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 启动时如果已登录（有 token），恢复用户信息到 store。
// 否则刷新页面后 store 是空的，MainLayout 的角色判断会失败、导航条会消失。
const userStore = useUserStore()
if (localStorage.getItem('access_token')) {
  userStore.fetchProfile()
}

app.mount('#app')
