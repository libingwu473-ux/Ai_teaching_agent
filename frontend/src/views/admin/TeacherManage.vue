<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">教师管理</h1>
        <p class="app-page-subtitle">管理可登录后台的教师账号，停用即软删除（保留历史数据）</p>
      </div>
      <el-button type="primary" @click="openCreate"><el-icon style="margin-right: 4px;"><Plus /></el-icon>新增教师</el-button>
    </div>

    <div class="app-card">
      <div class="app-toolbar">
        <el-input
          v-model="search"
          placeholder="搜索用户名 / 姓名"
          clearable
          style="width: 280px;"
          @keyup.enter="load"
          @clear="load"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-checkbox v-model="includeInactive" @change="load">含已停用</el-checkbox>
      </div>

      <el-table
        :data="teachers"
        v-loading="loading"
        empty-text="暂无教师"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="display_name" label="姓名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="160" :formatter="(r) => r.email || '—'" />
        <el-table-column prop="managed_class_count" label="管理班级" width="100" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', row.is_active ? 'is-success' : 'is-gray']">
              {{ row.is_active ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" min-width="160">
          <template #default="{ row }">{{ row.last_login ? formatDate(row.last_login) : '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
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
    <el-dialog v-model="modal.show" :title="modal.mode === 'create' ? '新增教师' : '编辑教师'" width="460px">
      <el-form ref="modalFormRef" :model="modal.form" :rules="modalRules" label-width="90px" label-position="right">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="modal.form.username" :disabled="modal.mode === 'edit'" placeholder="登录账号" />
        </el-form-item>
        <el-form-item v-if="modal.mode === 'create'" label="初始密码" prop="password">
          <el-input v-model="modal.form.password" placeholder="≥6 位，建议要求首次登录改密" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="modal.form.display_name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="modal.form.email" placeholder="可选" />
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
        将重置教师 <strong>{{ reset.target?.username }}</strong> 的密码
      </p>
      <el-input v-model="reset.newPassword" placeholder="新密码 ≥6 位" show-password />
      <template #footer>
        <el-button @click="reset.show = false">取消</el-button>
        <el-button type="primary" :loading="reset.saving" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listTeachers, createTeacher, updateTeacher, deactivateTeacher, resetTeacherPassword,
} from '../../api/admin'

const teachers = ref([])
const search = ref('')
const includeInactive = ref(false)
const loading = ref(false)

const modalFormRef = ref(null)
const modal = reactive({ show: false, mode: 'create', saving: false, form: {} })
const reset = reactive({ show: false, target: null, newPassword: '', saving: false })

const modalRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

async function load() {
  loading.value = true
  try {
    const params = {}
    if (search.value.trim()) params.search = search.value.trim()
    if (includeInactive.value) params.include_inactive = 1
    const resp = await listTeachers(params)
    teachers.value = resp.data.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { username: '', password: '', display_name: '', email: '' }
  modal.show = true
}
function openEdit(t) {
  modal.mode = 'edit'
  modal.form = { id: t.id, username: t.username, display_name: t.display_name, email: t.email }
  modal.show = true
}

async function submitModal() {
  if (!modalFormRef.value) return
  const valid = await modalFormRef.value.validate().catch(() => false)
  if (!valid) return
  modal.saving = true
  try {
    if (modal.mode === 'create') {
      await createTeacher(modal.form)
      ElMessage.success('教师已创建')
    } else {
      await updateTeacher(modal.form.id, {
        display_name: modal.form.display_name, email: modal.form.email,
      })
      ElMessage.success('已保存')
    }
    modal.show = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  } finally {
    modal.saving = false
  }
}

function openReset(t) {
  reset.target = t
  reset.newPassword = ''
  reset.show = true
}
async function submitReset() {
  if (!reset.newPassword || reset.newPassword.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  reset.saving = true
  try {
    await resetTeacherPassword(reset.target.id, reset.newPassword)
    ElMessage.success(`已重置 ${reset.target.username} 的密码`)
    reset.show = false
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  } finally {
    reset.saving = false
  }
}

async function deactivate(t) {
  try {
    await ElMessageBox.confirm(
      `确认停用教师 ${t.display_name || t.username}？停用后该教师无法登录，已有班级与历史记录保留。`,
      '停用确认', { type: 'warning' }
    )
    await deactivateTeacher(t.id)
    ElMessage.success('已停用')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.error || e.message || '操作失败')
  }
}
async function reactivate(t) {
  try {
    await updateTeacher(t.id, { is_active: true })
    ElMessage.success('已启用')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  }
}

onMounted(load)
</script>
