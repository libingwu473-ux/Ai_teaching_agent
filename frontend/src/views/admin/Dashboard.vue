<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>管理员控制台</h1>
      <p class="page-hint">超级管理员可在此管理教师账号、专业字典和 Dify 平台配置。</p>
    </div>
    <div class="grid">
      <router-link to="/admin/teachers" class="nav-card">
        <div class="nav-title">教师管理</div>
        <p>新增、停用、重置教师账号密码</p>
      </router-link>
      <router-link to="/admin/majors" class="nav-card">
        <div class="nav-title">专业管理</div>
        <p>维护学校专业字典</p>
      </router-link>
      <router-link to="/admin/dify-config" class="nav-card">
        <div class="nav-title">Dify 平台配置</div>
        <p>API 地址、API Key、SSL 校验等</p>
      </router-link>
    </div>
  </div>
</template>

<script setup></script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; padding: 24px 32px; height: 100%; overflow-y: auto; }
.page-header h1 { margin: 0; font-size: 24px; color: #1f2937; font-weight: 600; }
.page-hint { margin: 8px 0 24px; color: #6b7280; font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.nav-card { display: block; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; text-decoration: none; color: inherit; transition: border-color .15s, box-shadow .15s; }
.nav-card:hover { border-color: #4a90d9; box-shadow: 0 2px 6px rgba(74,144,217,.12); }
.nav-title { font-size: 16px; font-weight: 600; color: #1f2937; margin-bottom: 6px; }
.nav-card p { margin: 0; font-size: 13px; color: #6b7280; }
</style>
