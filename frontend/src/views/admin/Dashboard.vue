<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">管理员控制台</h1>
        <p class="app-page-subtitle">超级管理员可在此管理教师账号、专业字典和 Dify 平台配置</p>
      </div>
    </div>

    <div class="nav-grid">
      <router-link
        v-for="card in cards" :key="card.path"
        :to="card.path"
        class="nav-card"
      >
        <div class="nav-card-icon" :style="{ background: card.bg }">
          <el-icon><component :is="card.icon" /></el-icon>
        </div>
        <div class="nav-card-text">
          <div class="nav-card-title">{{ card.title }}</div>
          <p>{{ card.desc }}</p>
        </div>
        <el-icon class="nav-card-arrow"><ArrowRight /></el-icon>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { markRaw } from 'vue'
import { UserFilled, Reading, Connection, ArrowRight } from '@element-plus/icons-vue'

const cards = [
  { path: '/admin/teachers',    title: '教师管理',  desc: '新增、停用、重置教师账号密码',           icon: markRaw(UserFilled), bg: '#dbeafe' },
  { path: '/admin/majors',      title: '专业管理',  desc: '维护学校专业字典',                       icon: markRaw(Reading),    bg: '#dcfce7' },
  { path: '/admin/dify-config', title: 'Dify 平台配置', desc: 'API 地址、API Key、SSL 校验等',     icon: markRaw(Connection), bg: '#fef3c7' },
]
</script>

<style scoped>
.nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.nav-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-decoration: none;
  color: inherit;
  transition: transform var(--t-base), box-shadow var(--t-base), border-color var(--t-base);
}
.nav-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--brand-300);
}
.nav-card-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px;
  color: var(--brand-600);
  flex-shrink: 0;
}
.nav-card-text { flex: 1; min-width: 0; }
.nav-card-title { font-size: 15px; font-weight: 600; color: var(--gray-900); margin-bottom: 4px; }
.nav-card-text p { margin: 0; font-size: 13px; color: var(--gray-500); }
.nav-card-arrow { color: var(--gray-300); font-size: 18px; transition: transform var(--t-base), color var(--t-base); }
.nav-card:hover .nav-card-arrow { color: var(--brand-500); transform: translateX(4px); }
</style>
