<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">班级管理</h1>
        <p class="app-page-subtitle">一个教师可管理多个班级；一个班级只属于你。停用前请先把学生迁出</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon style="margin-right: 4px;"><Plus /></el-icon>新建班级
      </el-button>
    </div>

    <div class="app-card">
      <div class="app-toolbar">
        <el-checkbox v-model="includeInactive" @change="load">含已停用</el-checkbox>
      </div>

      <el-table :data="classes" v-loading="loading" empty-text="暂无班级，点击右上角新建" stripe style="width: 100%">
        <el-table-column label="专业" min-width="200">
          <template #default="{ row }">
            <span>{{ row.major_name }}</span>
            <el-tag size="small" type="info" style="margin-left: 8px;">{{ row.major_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="班级" min-width="140" />
        <el-table-column prop="student_count" label="学生数" width="100" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', row.is_active ? 'is-success' : 'is-gray']">
              {{ row.is_active ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <router-link :to="`/teacher/classes/${row.id}/students`" class="app-link" style="margin-right: 12px;">学生</router-link>
            <el-button link type="primary" @click="openEdit(row)">改名</el-button>
            <el-button v-if="row.is_active" link type="danger" @click="deactivate(row)">停用</el-button>
            <el-button v-else link type="primary" @click="reactivate(row)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="modal.show" :title="modal.mode === 'create' ? '新建班级' : '编辑班级'" width="460px">
      <el-form ref="modalFormRef" :model="modal.form" :rules="modalRules" label-width="80px">
        <el-form-item label="专业" prop="major_id">
          <el-select v-model="modal.form.major_id" :disabled="modal.mode === 'edit'" placeholder="请选择专业" style="width: 100%;">
            <el-option v-for="m in majors" :key="m.id" :value="m.id" :label="`${m.name} (${m.code})`" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级名称" prop="name">
          <el-input v-model="modal.form.name" placeholder="如 计科2401班" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modal.show = false">取消</el-button>
        <el-button type="primary" :loading="modal.saving" @click="submitModal">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listClasses, createClass, updateClass, deactivateClass, listMajorsReadonly,
} from '../../api/teacherClasses'

const classes = ref([])
const majors = ref([])
const includeInactive = ref(false)
const loading = ref(false)

const modalFormRef = ref(null)
const modal = reactive({ show: false, mode: 'create', saving: false, form: {} })
const modalRules = {
  major_id: [{ required: true, message: '请选择专业', trigger: 'change' }],
  name: [{ required: true, message: '请输入班级名称', trigger: 'blur' }],
}

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

async function load() {
  loading.value = true
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listClasses(params)
    classes.value = resp.data.data || []
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
  finally { loading.value = false }
}
async function loadMajors() {
  try { const resp = await listMajorsReadonly(); majors.value = resp.data.data || [] } catch (_) {}
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { major_id: majors.value[0]?.id ?? null, name: '' }
  modal.show = true
}
function openEdit(c) {
  modal.mode = 'edit'
  modal.form = { id: c.id, major_id: c.major_id, name: c.name }
  modal.show = true
}

async function submitModal() {
  if (!modalFormRef.value) return
  const valid = await modalFormRef.value.validate().catch(() => false)
  if (!valid) return
  modal.saving = true
  try {
    if (modal.mode === 'create') {
      await createClass({ major_id: modal.form.major_id, name: modal.form.name })
      ElMessage.success('班级已创建')
    } else {
      await updateClass(modal.form.id, { name: modal.form.name })
      ElMessage.success('已保存')
    }
    modal.show = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  } finally { modal.saving = false }
}

async function deactivate(c) {
  try {
    await ElMessageBox.confirm(`确认停用班级 ${c.name}？需先把学生全部停用或迁出。`, '停用确认', { type: 'warning' })
    await deactivateClass(c.id)
    ElMessage.success('已停用')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.error || e.message || '操作失败')
  }
}
async function reactivate(c) {
  try { await updateClass(c.id, { is_active: true }); ElMessage.success('已启用'); await load() }
  catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
}

onMounted(() => { load(); loadMajors() })
</script>
