<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">Dify 平台配置</h1>
        <p class="app-page-subtitle">修改后立即生效，所有用户的新对话将使用新配置；API 密钥留空则不修改</p>
      </div>
    </div>

    <el-card v-loading="!loaded" shadow="never" class="form-card">
      <el-form :model="form" label-width="120px" label-position="right" size="default">
        <el-form-item label="API 基础地址">
          <el-input v-model="form.api_base_url" placeholder="https://dify.example.com/v1" />
          <div class="form-hint">例如 <code>http://dify.chat.43d.cn/v1</code>，结尾的 <code>/</code> 会被自动去除</div>
        </el-form-item>

        <el-form-item label="API 密钥">
          <div style="display: flex; gap: 8px; width: 100%;">
            <el-input
              v-model="form.api_key"
              :type="showKey ? 'text' : 'password'"
              :placeholder="`当前: ${current.api_key_masked || '未设置'}（留空不修改）`"
              show-password
              style="flex: 1;"
            />
            <el-button @click="toggleReveal">
              {{ showKey ? '隐藏' : '显示当前' }}
            </el-button>
          </div>
          <div class="form-hint">形如 <code>app-xxxxxxxx</code></div>
        </el-form-item>

        <el-form-item label="Chatflow ID">
          <el-input v-model="form.chatflow_id" placeholder="6f0ca55a-b8ef-4f7d-a6a4-a0a3e18584ca" />
        </el-form-item>

        <el-form-item label="App ID">
          <el-input v-model="form.app_id" placeholder="可留空" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="请求超时(秒)">
              <el-input-number v-model="form.timeout" :min="1" :max="600" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大重试">
              <el-input-number v-model="form.max_retries" :min="0" :max="10" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="SSL 校验">
              <el-switch v-model="form.verify_ssl" />
              <span class="form-hint" style="margin-left: 10px;">Windows 上 SSL 错误可关闭</span>
            </el-form-item>
          </el-col>
        </el-row>

        <div v-if="current.updated_at" class="meta-line">
          最后修改：{{ formatDate(current.updated_at) }}
          <span v-if="current.updated_by">· 修改人：{{ current.updated_by }}</span>
        </div>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="reload(false)" :disabled="saving">重新加载</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDifyConfig, updateDifyConfig } from '../../api/teacher'

const loaded = ref(false)
const saving = ref(false)
const showKey = ref(false)
const current = ref({})
const form = reactive({
  api_base_url: '', api_key: '', app_id: '', chatflow_id: '',
  verify_ssl: false, timeout: 60, max_retries: 3,
})

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

async function reload(reveal = false) {
  try {
    const resp = await getDifyConfig(reveal)
    current.value = resp.data
    form.api_base_url = resp.data.api_base_url || ''
    form.app_id = resp.data.app_id || ''
    form.chatflow_id = resp.data.chatflow_id || ''
    form.verify_ssl = !!resp.data.verify_ssl
    form.timeout = resp.data.timeout ?? 60
    form.max_retries = resp.data.max_retries ?? 3
    form.api_key = reveal ? (resp.data.api_key || '') : ''
    showKey.value = reveal
    loaded.value = true
  } catch (e) {
    ElMessage.error('加载失败：' + (e.response?.data?.error || e.message))
  }
}

async function toggleReveal() {
  if (showKey.value) { showKey.value = false; form.api_key = '' }
  else { await reload(true) }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      api_base_url: form.api_base_url,
      app_id: form.app_id,
      chatflow_id: form.chatflow_id,
      verify_ssl: form.verify_ssl,
      timeout: form.timeout,
      max_retries: form.max_retries,
    }
    if (form.api_key && form.api_key.trim()) payload.api_key = form.api_key.trim()
    const resp = await updateDifyConfig(payload)
    current.value = resp.data
    form.api_key = ''
    showKey.value = false
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.error || e.message))
  } finally { saving.value = false }
}

onMounted(() => reload(false))
</script>

<style scoped>
.form-card { max-width: 760px; }
.form-hint { font-size: 12px; color: var(--gray-500); margin-top: 4px; line-height: 1.5; }
.form-hint code { background: var(--gray-100); padding: 1px 5px; border-radius: 3px; font-size: 11.5px; color: var(--gray-700); font-family: ui-monospace, Consolas, monospace; }
.meta-line { font-size: 12px; color: var(--gray-400); padding: 8px 0 16px; border-top: 1px dashed var(--gray-200); margin-top: 6px; }
</style>
