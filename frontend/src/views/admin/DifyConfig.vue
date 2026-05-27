<template>
  <div class="page">
    <div class="page-header">
      <router-link to="/admin/dashboard" class="back-link">← 返回管理员控制台</router-link>
      <h1>Dify 平台配置</h1>
      <p class="page-hint">修改后立即生效，所有用户新对话将使用新配置。API 密钥仅在保存时被替换 —— 留空表示不修改。</p>
    </div>

    <section class="card" v-if="loaded">
      <div class="field">
        <label>API 基础地址</label>
        <input v-model="form.api_base_url" placeholder="https://dify.example.com/v1" />
        <small>例如 <code>http://dify.chat.43d.cn/v1</code>，结尾的 <code>/</code> 会被自动去除。</small>
      </div>

      <div class="field">
        <label>API 密钥</label>
        <div class="key-row">
          <input
            v-model="form.api_key"
            :type="showKey ? 'text' : 'password'"
            :placeholder="`当前: ${current.api_key_masked || '未设置'}（留空不修改）`"
          />
          <button type="button" class="btn-secondary" @click="toggleReveal">
            {{ showKey ? '隐藏' : '显示当前' }}
          </button>
        </div>
        <small>形如 <code>app-xxxxxxxx</code>。</small>
      </div>

      <div class="field">
        <label>Chatflow ID</label>
        <input v-model="form.chatflow_id" placeholder="6f0ca55a-b8ef-4f7d-a6a4-a0a3e18584ca" />
      </div>

      <div class="field">
        <label>App ID（可选）</label>
        <input v-model="form.app_id" placeholder="可留空" />
      </div>

      <div class="field-grid">
        <div class="field">
          <label>请求超时 (秒)</label>
          <input v-model.number="form.timeout" type="number" min="1" max="600" />
        </div>
        <div class="field">
          <label>最大重试次数</label>
          <input v-model.number="form.max_retries" type="number" min="0" max="10" />
        </div>
        <div class="field">
          <label>SSL 校验</label>
          <label class="check-line">
            <input type="checkbox" v-model="form.verify_ssl" />
            <span>校验 SSL 证书</span>
          </label>
          <small>Windows 上常出现 SSL 错误，关闭可绕过。</small>
        </div>
      </div>

      <div class="meta" v-if="current.updated_at">
        最后修改：{{ formatDate(current.updated_at) }}
        <span v-if="current.updated_by">· 修改人：{{ current.updated_by }}</span>
      </div>

      <div class="actions">
        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="btn-secondary" :disabled="saving" @click="reload(false)">重新加载</button>
        <p v-if="message" :class="['inline-msg', messageType]">{{ message }}</p>
      </div>
    </section>
    <p v-else class="loading-hint">加载中...</p>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getDifyConfig, updateDifyConfig } from '../../api/teacher'

const loaded = ref(false)
const saving = ref(false)
const showKey = ref(false)
const message = ref('')
const messageType = ref('ok')
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
    message.value = '加载失败：' + (e.response?.data?.error || e.message)
    messageType.value = 'err'
  }
}

async function toggleReveal() {
  if (showKey.value) { showKey.value = false; form.api_key = '' }
  else { await reload(true) }
}

async function save() {
  saving.value = true; message.value = ''
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
    message.value = '已保存。'
    messageType.value = 'ok'
  } catch (e) {
    message.value = '保存失败：' + (e.response?.data?.error || e.message)
    messageType.value = 'err'
  } finally { saving.value = false }
}

onMounted(() => reload(false))
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 24px 32px 48px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 20px; }
.back-link { display: inline-block; margin-bottom: 8px; color: #4a90d9; text-decoration: none; font-size: 13px; }
.back-link:hover { text-decoration: underline; }
.page-header h1 { margin: 0 0 8px; font-size: 22px; color: #1f2937; font-weight: 600; }
.page-hint { color: #6b7280; font-size: 13px; margin: 0; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 24px; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 18px; }
.field > label { font-size: 13px; font-weight: 500; color: #374151; }
.field input { width: 100%; padding: 9px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.field input:focus { outline: none; border-color: #4a90d9; box-shadow: 0 0 0 3px rgba(74,144,217,.15); }
.field small { color: #6b7280; font-size: 12px; }
.field small code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 11.5px; color: #4b5563; }
.field-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px 20px; margin-bottom: 18px; }
.field-grid .field { margin-bottom: 0; }
.check-line { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #374151; font-weight: normal; padding: 8px 0; }
.check-line input[type="checkbox"] { width: 16px; height: 16px; margin: 0; }
.key-row { display: flex; gap: 8px; }
.key-row input { flex: 1; }
.meta { color: #9ca3af; font-size: 12px; margin: 4px 0 16px; padding-top: 12px; border-top: 1px dashed #e5e7eb; }
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 9px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-secondary:hover:not(:disabled) { background: #f9fafb; }
.inline-msg { margin: 0; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
.inline-msg.ok { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.inline-msg.err { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.loading-hint { color: #9ca3af; font-size: 14px; padding: 16px 0; }
</style>
