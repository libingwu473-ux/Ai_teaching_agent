<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <el-breadcrumb separator="/" style="margin-bottom: 8px;">
          <el-breadcrumb-item :to="{ path: '/teacher/classes' }">班级管理</el-breadcrumb-item>
          <el-breadcrumb-item>{{ info?.name || '加载中...' }}</el-breadcrumb-item>
        </el-breadcrumb>
        <h1 class="app-page-title">
          {{ info ? `${info.major_name} · ${info.name}` : '班级学生' }}
        </h1>
        <p class="app-page-subtitle">
          学生用户名 = 学号；初始密码 = 学号；学生首次登录后建议改密
        </p>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button @click="downloadTemplate"><el-icon style="margin-right: 4px;"><Download /></el-icon>CSV 模板</el-button>
        <el-button @click="openImport"><el-icon style="margin-right: 4px;"><Upload /></el-icon>批量导入</el-button>
        <el-button type="primary" @click="openCreate"><el-icon style="margin-right: 4px;"><Plus /></el-icon>录入学生</el-button>
      </div>
    </div>

    <div class="app-card">
      <div class="app-toolbar">
        <el-checkbox v-model="includeInactive" @change="load">含已停用</el-checkbox>
      </div>

      <el-table :data="students" v-loading="loading" empty-text="该班级暂无学生" stripe style="width: 100%">
        <el-table-column label="学号" width="160">
          <template #default="{ row }"><el-tag size="small" type="info">{{ row.username }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="display_name" label="姓名" min-width="120" />
        <el-table-column label="性别" width="80" align="center">
          <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', row.is_active ? 'is-success' : 'is-gray']">
              {{ row.is_active ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
            <el-button v-if="row.is_active" link type="danger" @click="deactivate(row)">停用</el-button>
            <el-button v-else link type="primary" @click="reactivate(row)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建 / 编辑 -->
    <el-dialog v-model="modal.show" :title="modal.mode === 'create' ? '录入学生' : '编辑学生'" width="460px">
      <el-form ref="modalFormRef" :model="modal.form" :rules="modalRules" label-width="90px">
        <el-form-item label="学号" prop="username">
          <el-input v-model="modal.form.username" :disabled="modal.mode === 'edit'" />
        </el-form-item>
        <el-form-item v-if="modal.mode === 'create'" label="初始密码">
          <el-input v-model="modal.form.password" placeholder="留空 = 学号" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="modal.form.display_name" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="modal.form.gender">
            <el-radio value="">未填</el-radio>
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
            <el-radio value="other">其他</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modal.show = false">取消</el-button>
        <el-button type="primary" :loading="modal.saving" @click="submitModal">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="reset.show" title="重置密码" width="420px">
      <p style="font-size: 13px; color: var(--gray-600); margin-bottom: 14px;">
        将重置学生 <strong>{{ reset.target?.username }}</strong> 的密码
      </p>
      <el-input v-model="reset.newPassword" placeholder="留空则重置为学号" show-password />
      <template #footer>
        <el-button @click="reset.show = false">取消</el-button>
        <el-button type="primary" :loading="reset.saving" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- CSV 导入 -->
    <el-dialog v-model="importM.show" title="CSV 批量导入学生" width="640px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="导入说明"
        style="margin-bottom: 16px;"
      >
        <template #default>
          <div style="font-size: 12.5px; line-height: 1.8;">
            表头：<code>学号,密码,专业,班别,姓名,性别</code><br />
            必填：学号、姓名；密码留空默认 = 学号；专业/班别需与本班一致；性别仅支持 男/女/其他/空<br />
            <strong>严格事务</strong>：任一行有错将不会导入任何记录
          </div>
        </template>
      </el-alert>

      <el-upload
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".csv"
        :on-change="onPickFile"
        :on-remove="() => importM.file = null"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽 CSV 文件到此 或 <em>点击选择</em></div>
      </el-upload>

      <div v-if="importM.result" style="margin-top: 14px;">
        <el-alert
          v-if="importM.result.success"
          type="success" :closable="false" show-icon
          :title="`导入成功，共 ${importM.result.imported} 条`"
        />
        <el-alert
          v-else
          type="error" :closable="false" show-icon
          :title="`导入失败（共 ${importM.result.failed} 行错误）`"
        >
          <ul style="max-height: 200px; overflow: auto; font-size: 12px; margin: 8px 0 0; padding-left: 20px;">
            <li v-for="(e, i) in importM.result.errors" :key="i">
              第 {{ e.row }} 行 [{{ e.username || '?' }}]：{{ e.reasons.join('；') }}
            </li>
          </ul>
        </el-alert>
      </div>

      <template #footer>
        <el-button @click="importM.show = false">关闭</el-button>
        <el-button type="primary" :disabled="!importM.file" :loading="importM.saving" @click="submitImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listClassStudents, createClassStudent, updateClassStudent, deactivateClassStudent,
  resetClassStudentPassword, importClassStudents, downloadCsvTemplate,
} from '../../api/teacherClasses'

const route = useRoute()
const classId = Number(route.params.id)

const students = ref([])
const info = ref(null)
const includeInactive = ref(false)
const loading = ref(false)

const modalFormRef = ref(null)
const modal = reactive({ show: false, mode: 'create', saving: false, form: {} })
const reset = reactive({ show: false, target: null, newPassword: '', saving: false })
const importM = reactive({ show: false, file: null, saving: false, result: null })

const modalRules = {
  username: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }
function genderLabel(g) { return ({ male: '男', female: '女', other: '其他' })[g] || '—' }

async function load() {
  loading.value = true
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listClassStudents(classId, params)
    students.value = resp.data.data || []
    info.value = resp.data.class || null
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
  finally { loading.value = false }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { username: '', password: '', display_name: '', gender: '' }
  modal.show = true
}
function openEdit(s) {
  modal.mode = 'edit'
  modal.form = { id: s.id, username: s.username, display_name: s.display_name, gender: s.gender || '' }
  modal.show = true
}

async function submitModal() {
  if (!modalFormRef.value) return
  const valid = await modalFormRef.value.validate().catch(() => false)
  if (!valid) return
  modal.saving = true
  try {
    if (modal.mode === 'create') {
      await createClassStudent(classId, modal.form)
      ElMessage.success('学生已录入')
    } else {
      await updateClassStudent(modal.form.id, {
        display_name: modal.form.display_name, gender: modal.form.gender,
      })
      ElMessage.success('已保存')
    }
    modal.show = false
    await load()
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
  finally { modal.saving = false }
}

function openReset(s) { reset.target = s; reset.newPassword = ''; reset.show = true }
async function submitReset() {
  reset.saving = true
  try {
    await resetClassStudentPassword(reset.target.id, reset.newPassword)
    ElMessage.success(`已重置 ${reset.target.username} 的密码为：${reset.newPassword || reset.target.username}`)
    reset.show = false
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
  finally { reset.saving = false }
}

async function deactivate(s) {
  try {
    await ElMessageBox.confirm(`确认停用学生 ${s.display_name}（${s.username}）？`, '停用确认', { type: 'warning' })
    await deactivateClassStudent(s.id)
    ElMessage.success('已停用')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.error || e.message || '操作失败')
  }
}
async function reactivate(s) {
  try { await updateClassStudent(s.id, { is_active: true }); ElMessage.success('已启用'); await load() }
  catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
}

function openImport() { importM.show = true; importM.file = null; importM.result = null }
function onPickFile(file) { importM.file = file.raw || file }

async function submitImport() {
  if (!importM.file) return
  importM.saving = true; importM.result = null
  try {
    const resp = await importClassStudents(classId, importM.file)
    importM.result = resp.data
    if (resp.data.success) await load()
  } catch (e) {
    const d = e.response?.data
    if (d && d.errors) importM.result = d
    else ElMessage.error(d?.error || e.message)
  } finally { importM.saving = false }
}

async function downloadTemplate() {
  try {
    const resp = await downloadCsvTemplate()
    const blob = new Blob([resp.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'students_template.csv'; a.click()
    URL.revokeObjectURL(url)
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
}

onMounted(load)
</script>

<style scoped>
code { background: var(--gray-100); padding: 1px 5px; border-radius: 3px; font-size: 11.5px; color: var(--gray-700); font-family: ui-monospace, Consolas, monospace; }
</style>
