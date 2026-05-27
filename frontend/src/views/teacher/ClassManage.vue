<template>
  <div class="page">
    <div class="page-header">
      <router-link to="/teacher/dashboard" class="back-link">← 返回仪表盘</router-link>
      <h1>班级管理</h1>
      <p class="page-hint">一个教师可管理多个班级；一个班级只属于你。停用班级前请先把学生迁出。</p>
    </div>

    <section class="card">
      <div class="toolbar">
        <label class="check-line"><input type="checkbox" v-model="includeInactive" @change="load" /> 含已停用</label>
        <button class="btn-primary" @click="openCreate">+ 新建班级</button>
      </div>
      <table class="data-table">
        <thead>
          <tr><th>专业</th><th>班级</th><th>学生数</th><th>状态</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in classes" :key="c.id">
            <td>{{ c.major_name }} <code>{{ c.major_code }}</code></td>
            <td>{{ c.name }}</td>
            <td>{{ c.student_count }}</td>
            <td><span :class="['badge', c.is_active ? 'ok' : 'off']">{{ c.is_active ? '启用' : '停用' }}</span></td>
            <td>{{ formatDate(c.created_at) }}</td>
            <td class="actions-cell">
              <router-link :to="`/teacher/classes/${c.id}/students`" class="link-btn">学生</router-link>
              <button class="link-btn" @click="openEdit(c)">改名</button>
              <button v-if="c.is_active" class="link-btn danger" @click="deactivate(c)">停用</button>
              <button v-else class="link-btn" @click="reactivate(c)">启用</button>
            </td>
          </tr>
          <tr v-if="!classes.length"><td colspan="6" class="empty">暂无班级，点击右上角新建</td></tr>
        </tbody>
      </table>
      <p v-if="error" class="err-msg">{{ error }}</p>
    </section>

    <div v-if="modal.show" class="modal-mask" @click.self="modal.show = false">
      <div class="modal">
        <h3>{{ modal.mode === 'create' ? '新建班级' : '编辑班级' }}</h3>
        <div class="field">
          <label>专业</label>
          <select v-model="modal.form.major_id" :disabled="modal.mode === 'edit'">
            <option :value="null" disabled>请选择专业</option>
            <option v-for="m in majors" :key="m.id" :value="m.id">{{ m.name }} ({{ m.code }})</option>
          </select>
        </div>
        <div class="field">
          <label>班级名称</label>
          <input v-model="modal.form.name" placeholder="如 计科2401班" />
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  listClasses, createClass, updateClass, deactivateClass, listMajorsReadonly,
} from '../../api/teacherClasses'

const classes = ref([])
const majors = ref([])
const includeInactive = ref(false)
const error = ref('')
const modal = reactive({ show: false, mode: 'create', saving: false, error: '', form: {} })

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

async function load() {
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listClasses(params)
    classes.value = resp.data.data || []
    error.value = ''
  } catch (e) { error.value = e.response?.data?.error || e.message }
}
async function loadMajors() {
  try { const resp = await listMajorsReadonly(); majors.value = resp.data.data || [] } catch (_) {}
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { major_id: majors.value[0]?.id ?? null, name: '' }
  modal.error = ''
  modal.show = true
}
function openEdit(c) {
  modal.mode = 'edit'
  modal.form = { id: c.id, major_id: c.major_id, name: c.name }
  modal.error = ''
  modal.show = true
}

async function submitModal() {
  modal.saving = true; modal.error = ''
  try {
    if (modal.mode === 'create') {
      await createClass({ major_id: modal.form.major_id, name: modal.form.name })
    } else {
      await updateClass(modal.form.id, { name: modal.form.name })
    }
    modal.show = false
    await load()
  } catch (e) {
    modal.error = e.response?.data?.error || e.message
  } finally { modal.saving = false }
}

async function deactivate(c) {
  if (!confirm(`确认停用班级 ${c.name}？需先把学生全部停用或迁出。`)) return
  try { await deactivateClass(c.id); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
}
async function reactivate(c) {
  try { await updateClass(c.id, { is_active: true }); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
}

onMounted(() => { load(); loadMajors() })
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 24px 32px 48px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 20px; }
.back-link { display: inline-block; margin-bottom: 8px; color: #4a90d9; text-decoration: none; font-size: 13px; }
.back-link:hover { text-decoration: underline; }
.page-header h1 { margin: 0 0 6px; font-size: 22px; color: #1f2937; font-weight: 600; }
.page-hint { font-size: 13px; color: #6b7280; margin: 0; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; }
.check-line { font-size: 13px; color: #4b5563; display: flex; align-items: center; gap: 6px; margin-right: auto; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
.data-table th { background: #fafbfc; color: #6b7280; font-weight: 500; }
.actions-cell { display: flex; gap: 10px; }
.link-btn { background: none; border: none; color: #4a90d9; cursor: pointer; padding: 0; font-size: 13px; text-decoration: none; }
.link-btn:hover { text-decoration: underline; }
.link-btn.danger { color: #b91c1c; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.ok { background: #ecfdf5; color: #047857; }
.badge.off { background: #fef2f2; color: #b91c1c; }
.empty { text-align: center; color: #9ca3af; padding: 24px; }
.err-msg { color: #b91c1c; font-size: 13px; margin-top: 10px; }
code { background: #f3f4f6; padding: 1px 6px; border-radius: 3px; font-size: 12px; color: #4b5563; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; padding: 24px; border-radius: 10px; width: 420px; max-width: 90vw; }
.modal h3 { margin: 0 0 16px; font-size: 16px; color: #1f2937; }
.modal .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.modal .field label { font-size: 13px; color: #374151; font-weight: 500; }
.modal .field input, .modal .field select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
</style>
