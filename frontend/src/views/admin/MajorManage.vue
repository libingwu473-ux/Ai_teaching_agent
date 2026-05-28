<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">专业管理</h1>
        <p class="app-page-subtitle">维护学校专业字典；专业下不可有启用中的班级才能停用</p>
      </div>
      <el-button type="primary" @click="openCreate"><el-icon style="margin-right: 4px;"><Plus /></el-icon>新增专业</el-button>
    </div>

    <div class="app-card">
      <div class="app-toolbar">
        <el-checkbox v-model="includeInactive" @change="load">含已停用</el-checkbox>
      </div>

      <el-table :data="majors" v-loading="loading" empty-text="暂无专业" stripe style="width: 100%">
        <el-table-column label="代码" width="160">
          <template #default="{ row }"><el-tag type="info" size="small">{{ row.code }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="200" :formatter="(r) => r.description || '—'" />
        <el-table-column prop="class_count" label="启用班级" width="100" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', row.is_active ? 'is-success' : 'is-gray']">
              {{ row.is_active ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.is_active" link type="danger" @click="deactivate(row)">停用</el-button>
            <el-button v-else link type="primary" @click="reactivate(row)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="modal.show" :title="modal.mode === 'create' ? '新增专业' : '编辑专业'" width="460px">
      <el-form ref="modalFormRef" :model="modal.form" :rules="modalRules" label-width="80px" label-position="right">
        <el-form-item label="代码" prop="code">
          <el-input v-model="modal.form.code" :disabled="modal.mode === 'edit'" placeholder="如 CS / DS2024" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="modal.form.name" placeholder="如 计算机科学与技术" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="modal.form.description" type="textarea" :rows="2" placeholder="可选" />
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
import { listMajors, createMajor, updateMajor, deactivateMajor } from '../../api/admin'

const majors = ref([])
const includeInactive = ref(false)
const loading = ref(false)

const modalFormRef = ref(null)
const modal = reactive({ show: false, mode: 'create', saving: false, form: {} })
const modalRules = {
  code: [{ required: true, message: '请输入专业代码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入专业名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const params = includeInactive.value ? { include_inactive: 1 } : {}
    const resp = await listMajors(params)
    majors.value = resp.data.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  modal.mode = 'create'
  modal.form = { code: '', name: '', description: '' }
  modal.show = true
}
function openEdit(m) {
  modal.mode = 'edit'
  modal.form = { id: m.id, code: m.code, name: m.name, description: m.description }
  modal.show = true
}

async function submitModal() {
  if (!modalFormRef.value) return
  const valid = await modalFormRef.value.validate().catch(() => false)
  if (!valid) return
  modal.saving = true
  try {
    if (modal.mode === 'create') {
      await createMajor(modal.form)
      ElMessage.success('专业已创建')
    } else {
      await updateMajor(modal.form.id, { name: modal.form.name, description: modal.form.description })
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

async function deactivate(m) {
  try {
    await ElMessageBox.confirm(`确认停用专业 ${m.name}？该专业下不能存在启用班级。`, '停用确认', { type: 'warning' })
    await deactivateMajor(m.id)
    ElMessage.success('已停用')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.error || e.message || '操作失败')
  }
}
async function reactivate(m) {
  try {
    await updateMajor(m.id, { is_active: true })
    ElMessage.success('已启用')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message)
  }
}

onMounted(load)
</script>
