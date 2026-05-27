<template>
  <div class="page">
    <div class="page-header">
      <router-link to="/teacher/classes" class="back-link">← 返回班级列表</router-link>
      <h1 v-if="info">{{ info.major_name }} · {{ info.name }}</h1>
      <p class="page-hint">学生用户名 = 学号；初始密码 = 学号；学生首次登录后建议修改密码。</p>
    </div>

    <section class="card">
      <div class="toolbar">
        <label class="check-line"><input type="checkbox" v-model="includeInactive" @change="load" /> 含已停用</label>
        <button class="btn-primary" @click="openCreate">+ 录入学生</button>
        <button class="btn-secondary" @click="openImport">CSV 批量导入</button>
        <button class="btn-secondary" @click="downloadTemplate">下载 CSV 模板</button>
      </div>

      <table class="data-table">
        <thead>
          <tr><th>学号</th><th>姓名</th><th>性别</th><th>状态</th><th>注册时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="s in students" :key="s.id">
            <td><code>{{ s.username }}</code></td>
            <td>{{ s.display_name }}</td>
            <td>{{ genderLabel(s.gender) }}</td>
            <td><span :class="['badge', s.is_active ? 'ok' : 'off']">{{ s.is_active ? '启用' : '停用' }}</span></td>
            <td>{{ formatDate(s.date_joined) }}</td>
            <td class="actions-cell">
              <button class="link-btn" @click="openEdit(s)">编辑</button>
              <button class="link-btn" @click="openReset(s)">重置密码</button>
              <button v-if="s.is_active" class="link-btn danger" @click="deactivate(s)">停用</button>
              <button v-else class="link-btn" @click="reactivate(s)">启用</button>
            </td>
          </tr>
          <tr v-if="!students.length"><td colspan="6" class="empty">该班级暂无学生</td></tr>
        </tbody>
      </table>
      <p v-if="error" class="err-msg">{{ error }}</p>
    </section>

    <!-- 创建/编辑 -->
    <div v-if="modal.show" class="modal-mask" @click.self="modal.show = false">
      <div class="modal">
        <h3>{{ modal.mode === 'create' ? '录入学生' : '编辑学生' }}</h3>
        <div class="field">
          <label>学号</label>
          <input v-model="modal.form.username" :disabled="modal.mode === 'edit'" />
        </div>
        <div class="field" v-if="modal.mode === 'create'">
          <label>初始密码（留空则使用学号）</label>
          <input v-model="modal.form.password" placeholder="留空 = 学号" />
        </div>
        <div class="field">
          <label>姓名</label>
          <input v-model="modal.form.display_name" />
        </div>
        <div class="field">
          <label>性别</label>
          <select v-model="modal.form.gender">
            <option value="">未填</option>
            <option value="male">男</option>
            <option value="female">女</option>
            <option value="other">其他</option>
          </select>
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

    <!-- 重置密码 -->
    <div v-if="reset.show" class="modal-mask" @click.self="reset.show = false">
      <div class="modal">
        <h3>重置密码：{{ reset.target?.username }}</h3>
        <div class="field">
          <label>新密码（留空则重置为学号）</label>
          <input v-model="reset.newPassword" placeholder="留空 = 学号" />
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

    <!-- CSV 导入 -->
    <div v-if="importM.show" class="modal-mask" @click.self="importM.show = false">
      <div class="modal" style="width: 560px;">
        <h3>CSV 批量导入学生</h3>
        <p class="hint">
          表头：<code>学号,密码,专业,班别,姓名,性别</code><br />
          必填：学号、姓名；密码留空默认 = 学号；专业/班别需与本班一致；性别仅支持 男/女/其他/空。<br />
          严格事务：任一行有错将不会导入任何记录。
        </p>
        <input type="file" accept=".csv" @change="onPickFile" />
        <div class="modal-actions">
          <button class="btn-secondary" @click="importM.show = false">取消</button>
          <button class="btn-primary" :disabled="!importM.file || importM.saving" @click="submitImport">
            {{ importM.saving ? '导入中...' : '开始导入' }}
          </button>
        </div>
        <div v-if="importM.result" class="import-result">
          <p v-if="importM.result.success" class="ok-text">✅ 导入成功，共 {{ importM.result.imported }} 条</p>
          <div v-else>
            <p class="err-text">导入失败（共 {{ importM.result.failed }} 行错误）：</p>
            <ul class="error-list">
              <li v-for="(e, i) in importM.result.errors" :key="i">
                第 {{ e.row }} 行 [{{ e.username || '?' }}]：{{ e.reasons.join('；') }}
              </li>
            </ul>
          </div>
        </div>
        <p v-if="importM.error" class="err-msg">{{ importM.error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  listClassStudents, createClassStudent, updateClassStudent, deactivateClassStudent,
  resetClassStudentPassword, importClassStudents, downloadCsvTemplate,
} from '../../api/teacherClasses'

const route = useRoute()
const classId = Number(route.params.id)

const students = ref([])
const info = ref(null)
const includeInactive = ref(false)
const error = ref('')

const modal = reactive({ show: false, mode: 'create', saving: false, error: '', form: {} })
const reset = reactive({ show: false, target: null, newPassword: '', saving: false, error: '' })
const importM = reactive({ show: false, file: null, saving: false, error: '', result: null })

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }
function genderLabel(g) { return ({ male: '男', female: '女', other: '其他' })[g] || '—' }

async function load() {
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listClassStudents(classId, params)
    students.value = resp.data.data || []
    info.value = resp.data.class || null
    error.value = ''
  } catch (e) { error.value = e.response?.data?.error || e.message }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { username: '', password: '', display_name: '', gender: '' }
  modal.error = ''
  modal.show = true
}
function openEdit(s) {
  modal.mode = 'edit'
  modal.form = { id: s.id, username: s.username, display_name: s.display_name, gender: s.gender || '' }
  modal.error = ''
  modal.show = true
}

async function submitModal() {
  modal.saving = true; modal.error = ''
  try {
    if (modal.mode === 'create') {
      await createClassStudent(classId, modal.form)
    } else {
      await updateClassStudent(modal.form.id, {
        display_name: modal.form.display_name,
        gender: modal.form.gender,
      })
    }
    modal.show = false
    await load()
  } catch (e) {
    modal.error = e.response?.data?.error || e.message
  } finally { modal.saving = false }
}

function openReset(s) { reset.target = s; reset.newPassword = ''; reset.error = ''; reset.show = true }

async function submitReset() {
  reset.saving = true; reset.error = ''
  try {
    await resetClassStudentPassword(reset.target.id, reset.newPassword)
    reset.show = false
    alert(`已重置 ${reset.target.username} 的密码为：${reset.newPassword || reset.target.username}`)
  } catch (e) {
    reset.error = e.response?.data?.error || e.message
  } finally { reset.saving = false }
}

async function deactivate(s) {
  if (!confirm(`确认停用学生 ${s.display_name}（${s.username}）？`)) return
  try { await deactivateClassStudent(s.id); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
}
async function reactivate(s) {
  try { await updateClassStudent(s.id, { is_active: true }); await load() }
  catch (e) { alert(e.response?.data?.error || e.message) }
}

function openImport() { importM.show = true; importM.file = null; importM.error = ''; importM.result = null }
function onPickFile(e) { importM.file = e.target.files?.[0] || null }

async function submitImport() {
  if (!importM.file) return
  importM.saving = true; importM.error = ''; importM.result = null
  try {
    const resp = await importClassStudents(classId, importM.file)
    importM.result = resp.data
    if (resp.data.success) {
      await load()
    }
  } catch (e) {
    const d = e.response?.data
    if (d && d.errors) importM.result = d
    else importM.error = d?.error || e.message
  } finally { importM.saving = false }
}

async function downloadTemplate() {
  try {
    const resp = await downloadCsvTemplate()
    const blob = new Blob([resp.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'students_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert(e.response?.data?.error || e.message) }
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 24px 32px 48px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 20px; }
.back-link { display: inline-block; margin-bottom: 8px; color: #4a90d9; text-decoration: none; font-size: 13px; }
.back-link:hover { text-decoration: underline; }
.page-header h1 { margin: 0 0 6px; font-size: 22px; color: #1f2937; font-weight: 600; }
.page-hint { font-size: 13px; color: #6b7280; margin: 0; }
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
.actions-cell { display: flex; gap: 8px; flex-wrap: wrap; }
.link-btn { background: none; border: none; color: #4a90d9; cursor: pointer; padding: 0; font-size: 13px; }
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
.modal h3 { margin: 0 0 12px; font-size: 16px; color: #1f2937; }
.modal .hint { font-size: 12.5px; color: #6b7280; line-height: 1.6; margin: 0 0 14px; }
.modal .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.modal .field label { font-size: 13px; color: #374151; font-weight: 500; }
.modal .field input, .modal .field select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 10px; }
.import-result { margin-top: 14px; }
.ok-text { color: #047857; }
.err-text { color: #b91c1c; }
.error-list { max-height: 200px; overflow: auto; font-size: 12.5px; color: #b91c1c; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 8px 16px; }
</style>
