<template>
  <div class="page">
    <div class="page-header">
      <router-link to="/admin/dashboard" class="back-link">← 返回管理员控制台</router-link>
      <h1>教师管理</h1>
    </div>

    <section class="card">
      <div class="toolbar">
        <input v-model="search" placeholder="搜索用户名/姓名" class="search" @keyup.enter="load" />
        <label class="check-line"><input type="checkbox" v-model="includeInactive" @change="load" /> 含已停用</label>
        <button class="btn-primary" @click="openCreate">+ 新增教师</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>用户名</th><th>姓名</th><th>邮箱</th><th>已管理班级</th><th>状态</th><th>最近登录</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in teachers" :key="t.id">
            <td>{{ t.username }}</td>
            <td>{{ t.display_name }}</td>
            <td>{{ t.email || '—' }}</td>
            <td>{{ t.managed_class_count }}</td>
            <td><span :class="['badge', t.is_active ? 'ok' : 'off']">{{ t.is_active ? '启用' : '停用' }}</span></td>
            <td>{{ t.last_login ? formatDate(t.last_login) : '—' }}</td>
            <td class="actions-cell">
              <button class="link-btn" @click="openEdit(t)">编辑</button>
              <button class="link-btn" @click="openReset(t)">重置密码</button>
              <button v-if="t.is_active" class="link-btn danger" @click="deactivate(t)">停用</button>
              <button v-else class="link-btn" @click="reactivate(t)">启用</button>
            </td>
          </tr>
          <tr v-if="!teachers.length"><td colspan="7" class="empty">暂无数据</td></tr>
        </tbody>
      </table>
      <p v-if="error" class="err-msg">{{ error }}</p>
    </section>

    <!-- 创建/编辑弹窗 -->
    <div v-if="modal.show" class="modal-mask" @click.self="modal.show = false">
      <div class="modal">
        <h3>{{ modal.mode === 'create' ? '新增教师' : '编辑教师' }}</h3>
        <div class="field">
          <label>用户名（登录账号）</label>
          <input v-model="modal.form.username" :disabled="modal.mode === 'edit'" />
        </div>
        <div class="field" v-if="modal.mode === 'create'">
          <label>初始密码（≥6 位）</label>
          <input v-model="modal.form.password" type="text" />
        </div>
        <div class="field">
          <label>姓名（显示名）</label>
          <input v-model="modal.form.display_name" />
        </div>
        <div class="field">
          <label>邮箱（可选）</label>
          <input v-model="modal.form.email" />
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="modal.show = false">取消</button>
          <button class="btn-primary" :disabled="modal.saving" @click="submitModal">
            {{ modal.saving ? '保存中...' : '保存' }}
          </button>
        </div>
        <p v-if="modal.error" class="err-msg">{{ modal.error }}</p>
      </div>
    </div>

    <!-- 重置密码弹窗 -->
    <div v-if="reset.show" class="modal-mask" @click.self="reset.show = false">
      <div class="modal">
        <h3>重置密码：{{ reset.target?.username }}</h3>
        <div class="field">
          <label>新密码（≥6 位）</label>
          <input v-model="reset.newPassword" type="text" />
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="reset.show = false">取消</button>
          <button class="btn-primary" :disabled="reset.saving" @click="submitReset">
            {{ reset.saving ? '提交中...' : '确认重置' }}
          </button>
        </div>
        <p v-if="reset.error" class="err-msg">{{ reset.error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  listTeachers, createTeacher, updateTeacher, deactivateTeacher, resetTeacherPassword,
} from '../../api/admin'

const teachers = ref([])
const search = ref('')
const includeInactive = ref(false)
const error = ref('')

const modal = reactive({ show: false, mode: 'create', saving: false, error: '', form: {} })
const reset = reactive({ show: false, target: null, newPassword: '', saving: false, error: '' })

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

async function load() {
  try {
    const params = {}
    if (search.value.trim()) params.search = search.value.trim()
    if (includeInactive.value) params.include_inactive = 1
    const resp = await listTeachers(params)
    teachers.value = resp.data.data || []
    error.value = ''
  } catch (e) {
    error.value = e.response?.data?.error || e.message
  }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { username: '', password: '', display_name: '', email: '' }
  modal.error = ''
  modal.show = true
}

function openEdit(t) {
  modal.mode = 'edit'
  modal.form = { id: t.id, username: t.username, display_name: t.display_name, email: t.email }
  modal.error = ''
  modal.show = true
}

async function submitModal() {
  modal.saving = true
  modal.error = ''
  try {
    if (modal.mode === 'create') {
      await createTeacher(modal.form)
    } else {
      await updateTeacher(modal.form.id, {
        display_name: modal.form.display_name,
        email: modal.form.email,
      })
    }
    modal.show = false
    await load()
  } catch (e) {
    modal.error = e.response?.data?.error || e.message
  } finally {
    modal.saving = false
  }
}

function openReset(t) {
  reset.target = t
  reset.newPassword = ''
  reset.error = ''
  reset.show = true
}

async function submitReset() {
  reset.saving = true
  reset.error = ''
  try {
    await resetTeacherPassword(reset.target.id, reset.newPassword)
    reset.show = false
  } catch (e) {
    reset.error = e.response?.data?.error || e.message
  } finally {
    reset.saving = false
  }
}

async function deactivate(t) {
  if (!confirm(`确认停用教师 ${t.display_name || t.username}？停用后该教师无法登录，但已有班级与历史记录保留。`)) return
  try {
    await deactivateTeacher(t.id)
    await load()
  } catch (e) {
    alert(e.response?.data?.error || e.message)
  }
}

async function reactivate(t) {
  try {
    await updateTeacher(t.id, { is_active: true })
    await load()
  } catch (e) {
    alert(e.response?.data?.error || e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 24px 32px 48px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 20px; }
.back-link { display: inline-block; margin-bottom: 8px; color: #4a90d9; text-decoration: none; font-size: 13px; }
.back-link:hover { text-decoration: underline; }
.page-header h1 { margin: 0; font-size: 22px; color: #1f2937; font-weight: 600; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.search { flex: 1; min-width: 200px; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.check-line { font-size: 13px; color: #4b5563; display: flex; align-items: center; gap: 6px; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
.data-table th { background: #fafbfc; color: #6b7280; font-weight: 500; }
.actions-cell { display: flex; gap: 8px; flex-wrap: wrap; }
.link-btn { background: none; border: none; color: #4a90d9; cursor: pointer; padding: 0; font-size: 13px; }
.link-btn:hover { text-decoration: underline; }
.link-btn.danger { color: #b91c1c; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.ok { background: #ecfdf5; color: #047857; }
.badge.off { background: #fef2f2; color: #b91c1c; }
.empty { text-align: center; color: #9ca3af; padding: 24px; }
.err-msg { color: #b91c1c; font-size: 13px; margin-top: 10px; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; padding: 24px; border-radius: 10px; width: 420px; max-width: 90vw; }
.modal h3 { margin: 0 0 16px; font-size: 16px; color: #1f2937; }
.modal .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.modal .field label { font-size: 13px; color: #374151; font-weight: 500; }
.modal .field input { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
</style>
