<template>
  <div class="page">
    <div class="page-header">
      <router-link to="/admin/dashboard" class="back-link">← 返回管理员控制台</router-link>
      <h1>专业管理</h1>
    </div>
    <section class="card">
      <div class="toolbar">
        <label class="check-line"><input type="checkbox" v-model="includeInactive" @change="load" /> 含已停用</label>
        <button class="btn-primary" @click="openCreate">+ 新增专业</button>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>代码</th><th>名称</th><th>描述</th><th>启用班级数</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in majors" :key="m.id">
            <td><code>{{ m.code }}</code></td>
            <td>{{ m.name }}</td>
            <td>{{ m.description || '—' }}</td>
            <td>{{ m.class_count }}</td>
            <td><span :class="['badge', m.is_active ? 'ok' : 'off']">{{ m.is_active ? '启用' : '停用' }}</span></td>
            <td class="actions-cell">
              <button class="link-btn" @click="openEdit(m)">编辑</button>
              <button v-if="m.is_active" class="link-btn danger" @click="deactivate(m)">停用</button>
              <button v-else class="link-btn" @click="reactivate(m)">启用</button>
            </td>
          </tr>
          <tr v-if="!majors.length"><td colspan="6" class="empty">暂无数据</td></tr>
        </tbody>
      </table>
      <p v-if="error" class="err-msg">{{ error }}</p>
    </section>

    <div v-if="modal.show" class="modal-mask" @click.self="modal.show = false">
      <div class="modal">
        <h3>{{ modal.mode === 'create' ? '新增专业' : '编辑专业' }}</h3>
        <div class="field">
          <label>专业代码</label>
          <input v-model="modal.form.code" :disabled="modal.mode === 'edit'" placeholder="如 CS / DS2024" />
        </div>
        <div class="field">
          <label>名称</label>
          <input v-model="modal.form.name" placeholder="如 计算机科学与技术" />
        </div>
        <div class="field">
          <label>描述（可选）</label>
          <input v-model="modal.form.description" />
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
import { listMajors, createMajor, updateMajor, deactivateMajor } from '../../api/admin'

const majors = ref([])
const includeInactive = ref(false)
const error = ref('')
const modal = reactive({ show: false, mode: 'create', saving: false, error: '', form: {} })

async function load() {
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listMajors(params)
    majors.value = resp.data.data || []
    error.value = ''
  } catch (e) {
    error.value = e.response?.data?.error || e.message
  }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { code: '', name: '', description: '' }
  modal.error = ''
  modal.show = true
}
function openEdit(m) {
  modal.mode = 'edit'
  modal.form = { id: m.id, code: m.code, name: m.name, description: m.description }
  modal.error = ''
  modal.show = true
}

async function submitModal() {
  modal.saving = true
  modal.error = ''
  try {
    if (modal.mode === 'create') {
      await createMajor(modal.form)
    } else {
      await updateMajor(modal.form.id, { name: modal.form.name, description: modal.form.description })
    }
    modal.show = false
    await load()
  } catch (e) {
    modal.error = e.response?.data?.error || e.message
  } finally {
    modal.saving = false
  }
}

async function deactivate(m) {
  if (!confirm(`确认停用专业 ${m.name}？专业下不能存在启用中的班级。`)) return
  try { await deactivateMajor(m.id); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
}
async function reactivate(m) {
  try { await updateMajor(m.id, { is_active: true }); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
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
.check-line { font-size: 13px; color: #4b5563; display: flex; align-items: center; gap: 6px; margin-right: auto; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
.data-table th { background: #fafbfc; color: #6b7280; font-weight: 500; }
.actions-cell { display: flex; gap: 8px; }
.link-btn { background: none; border: none; color: #4a90d9; cursor: pointer; padding: 0; font-size: 13px; }
.link-btn:hover { text-decoration: underline; }
.link-btn.danger { color: #b91c1c; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.ok { background: #ecfdf5; color: #047857; }
.badge.off { background: #fef2f2; color: #b91c1c; }
.empty { text-align: center; color: #9ca3af; padding: 24px; }
.err-msg { color: #b91c1c; font-size: 13px; margin-top: 10px; }
code { background: #f3f4f6; padding: 1px 6px; border-radius: 3px; font-size: 12.5px; color: #4b5563; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; padding: 24px; border-radius: 10px; width: 420px; max-width: 90vw; }
.modal h3 { margin: 0 0 16px; font-size: 16px; color: #1f2937; }
.modal .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.modal .field label { font-size: 13px; color: #374151; font-weight: 500; }
.modal .field input { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
</style>
