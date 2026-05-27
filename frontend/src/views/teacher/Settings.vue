<template>
  <div class="settings-page">
    <router-link to="/teacher/dashboard" class="back-link">&larr; 返回仪表盘</router-link>
    <h1>系统配置 · Dify 平台</h1>
    <p class="hint">修改后立即生效，所有用户的新对话都将使用新配置。API 密钥仅在保存时被替换 —— 留空表示不修改。</p>

    <div class="card" v-if="loaded">
      <div class="form-group">
        <label>API 基础地址</label>
        <input v-model="form.api_base_url" placeholder="https://dify.example.com/v1" />
        <small>例如 <code>http://dify.chat.43d.cn/v1</code>，结尾的 <code>/</code> 会被自动去除。</small>
      </div>

      <div class="form-group">
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

      <div class="form-group">
        <label>Chatflow ID</label>
        <input v-model="form.chatflow_id" placeholder="6f0ca55a-b8ef-4f7d-a6a4-a0a3e18584ca" />
        <small>对应 Dify 后台的 chatflow / workflow ID（仅记录，便于追溯）。</small>
      </div>

      <div class="form-group">
        <label>App ID（可选）</label>
        <input v-model="form.app_id" placeholder="可留空" />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>请求超时 (秒)</label>
          <input v-model.number="form.timeout" type="number" min="1" max="600" />
        </div>
        <div class="form-group">
          <label>最大重试次数</label>
          <input v-model.number="form.max_retries" type="number" min="0" max="10" />
        </div>
        <div class="form-group checkbox-group">
          <label>
            <input type="checkbox" v-model="form.verify_ssl" />
            校验 SSL 证书
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
        <button class="btn-secondary" :disabled="saving" @click="reload">重新加载</button>
      </div>

      <p v-if="message" :class="['msg', messageType]">{{ message }}</p>
    </div>

    <h1 style="margin-top: 32px;">评分参数</h1>
    <p class="hint">修改后会影响后续的评分计算；可在仪表盘点"重算全部评分"对历史会话生效。</p>

    <div class="card" v-if="scoringLoaded">
      <div class="form-row">
        <div class="form-group">
          <label>阶段完成度权重</label>
          <input v-model.number="scoringForm.stage_completion_weight" type="number" min="0" max="1" step="0.05" />
        </div>
        <div class="form-group">
          <label>流程遵循度权重</label>
          <input v-model.number="scoringForm.sequence_adherence_weight" type="number" min="0" max="1" step="0.05" />
        </div>
        <div class="form-group">
          <label>时间投入权重</label>
          <input v-model.number="scoringForm.time_investment_weight" type="number" min="0" max="1" step="0.05" />
        </div>
        <div class="form-group">
          <label>参与度权重</label>
          <input v-model.number="scoringForm.engagement_weight" type="number" min="0" max="1" step="0.05" />
        </div>
      </div>
      <p class="hint" :class="{ 'weight-warn': !weightOk }">
        四项权重之和 = <strong>{{ weightSum.toFixed(2) }}</strong>（应当 ≈ 1.00）
      </p>

      <div class="form-row">
        <div class="form-group">
          <label>最小会话分钟</label>
          <input v-model.number="scoringForm.min_session_minutes" type="number" min="0" max="120" step="1" />
          <small>会话总时长低于此值时，"时间投入"维度直接判 0。设为 0 可关闭门槛。</small>
        </div>
        <div class="form-group">
          <label>满分</label>
          <input v-model.number="scoringForm.max_score" type="number" min="1" max="1000" step="1" />
        </div>
      </div>

      <div class="meta" v-if="scoringCurrent.updated_at">
        最后修改：{{ formatDate(scoringCurrent.updated_at) }}
        <span v-if="scoringCurrent.updated_by">· 修改人：{{ scoringCurrent.updated_by }}</span>
      </div>

      <div class="actions">
        <button class="btn-primary" :disabled="scoringSaving || !weightOk" @click="saveScoring">
          {{ scoringSaving ? '保存中...' : '保存' }}
        </button>
        <button class="btn-secondary" :disabled="scoringSaving" @click="loadScoring">重新加载</button>
      </div>

      <p v-if="scoringMessage" :class="['msg', scoringMessageType]">{{ scoringMessage }}</p>
    </div>

    <h1 style="margin-top: 32px;">阶段完成门槛</h1>
    <p class="hint">
      每个阶段需要的最少消息数。学生在该阶段累计消息数达到此值才会被判为"已完成"。设为 0 表示只要触达该阶段即视为完成。修改后可在仪表盘点"重算全部评分"对历史会话生效。
    </p>

    <div class="card" v-if="stagesLoaded">
      <p v-if="!stages.length" class="empty-hint">未找到教学流程，请先运行 <code>python manage.py seed_workflow</code>。</p>

      <table v-else class="stages-table">
        <thead>
          <tr>
            <th>阶段</th>
            <th>标识</th>
            <th style="width: 160px;">最少消息数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in stages" :key="s.id">
            <td>{{ s.name }}</td>
            <td><code>{{ s.stage_key }}</code></td>
            <td>
              <input v-model.number="s.expected_min_messages" type="number" min="0" max="999" step="1" />
            </td>
          </tr>
        </tbody>
      </table>

      <div class="actions" v-if="stages.length">
        <button class="btn-primary" :disabled="stagesSaving" @click="saveStages">
          {{ stagesSaving ? '保存中...' : '保存' }}
        </button>
        <button class="btn-secondary" :disabled="stagesSaving" @click="loadStages">重新加载</button>
      </div>

      <p v-if="stagesMessage" :class="['msg', stagesMessageType]">{{ stagesMessage }}</p>
    </div>

    <p v-else class="empty-hint">加载中...</p>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import {
  getDifyConfig, updateDifyConfig,
  getScoringConfig, updateScoringConfig,
  getWorkflowStages, updateWorkflowStages,
} from '../../api/teacher'

const loaded = ref(false)
const saving = ref(false)
const showKey = ref(false)
const message = ref('')
const messageType = ref('ok')

const scoringLoaded = ref(false)
const scoringSaving = ref(false)
const scoringMessage = ref('')
const scoringMessageType = ref('ok')
const scoringCurrent = ref({})
const scoringForm = reactive({
  stage_completion_weight: 0.40,
  sequence_adherence_weight: 0.25,
  time_investment_weight: 0.15,
  engagement_weight: 0.20,
  min_session_minutes: 5,
  max_score: 100,
})
const weightSum = computed(() =>
  (Number(scoringForm.stage_completion_weight) || 0) +
  (Number(scoringForm.sequence_adherence_weight) || 0) +
  (Number(scoringForm.time_investment_weight) || 0) +
  (Number(scoringForm.engagement_weight) || 0)
)
const weightOk = computed(() => weightSum.value >= 0.95 && weightSum.value <= 1.05)

const current = ref({})
const form = reactive({
  api_base_url: '',
  api_key: '',
  app_id: '',
  chatflow_id: '',
  verify_ssl: false,
  timeout: 60,
  max_retries: 3,
})

function formatDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

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
    form.api_key = reveal ? resp.data.api_key || '' : ''
    showKey.value = reveal
    loaded.value = true
  } catch (e) {
    message.value = '加载配置失败：' + (e.response?.data?.error || e.message)
    messageType.value = 'err'
  }
}

async function toggleReveal() {
  if (showKey.value) {
    showKey.value = false
    form.api_key = ''
  } else {
    await reload(true)
  }
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    const payload = {
      api_base_url: form.api_base_url,
      app_id: form.app_id,
      chatflow_id: form.chatflow_id,
      verify_ssl: form.verify_ssl,
      timeout: form.timeout,
      max_retries: form.max_retries,
    }
    if (form.api_key && form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    }
    const resp = await updateDifyConfig(payload)
    current.value = resp.data
    form.api_key = ''
    showKey.value = false
    message.value = '已保存。'
    messageType.value = 'ok'
  } catch (e) {
    message.value = '保存失败：' + (e.response?.data?.error || e.message)
    messageType.value = 'err'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  reload(false)
  loadScoring()
  loadStages()
})

async function loadScoring() {
  try {
    const resp = await getScoringConfig()
    scoringCurrent.value = resp.data
    scoringForm.stage_completion_weight = resp.data.stage_completion_weight
    scoringForm.sequence_adherence_weight = resp.data.sequence_adherence_weight
    scoringForm.time_investment_weight = resp.data.time_investment_weight
    scoringForm.engagement_weight = resp.data.engagement_weight
    scoringForm.min_session_minutes = resp.data.min_session_minutes
    scoringForm.max_score = resp.data.max_score
    scoringLoaded.value = true
  } catch (e) {
    scoringMessage.value = '加载评分参数失败：' + (e.response?.data?.error || e.message)
    scoringMessageType.value = 'err'
  }
}

async function saveScoring() {
  scoringSaving.value = true
  scoringMessage.value = ''
  try {
    const resp = await updateScoringConfig({ ...scoringForm })
    scoringCurrent.value = resp.data
    scoringMessage.value = '已保存。仪表盘点"重算全部评分"可让历史数据生效。'
    scoringMessageType.value = 'ok'
  } catch (e) {
    scoringMessage.value = '保存失败：' + (e.response?.data?.error || e.message)
    scoringMessageType.value = 'err'
  } finally {
    scoringSaving.value = false
  }
}

const stagesLoaded = ref(false)
const stagesSaving = ref(false)
const stagesMessage = ref('')
const stagesMessageType = ref('ok')
const stagesWorkflowName = ref('')
const stages = ref([])

async function loadStages() {
  try {
    const resp = await getWorkflowStages()
    stagesWorkflowName.value = resp.data.workflow_name || ''
    stages.value = (resp.data.stages || []).map((s) => ({ ...s }))
    stagesLoaded.value = true
  } catch (e) {
    stagesMessage.value = '加载阶段配置失败：' + (e.response?.data?.error || e.message)
    stagesMessageType.value = 'err'
  }
}

async function saveStages() {
  stagesSaving.value = true
  stagesMessage.value = ''
  try {
    const updates = stages.value.map((s) => ({
      id: s.id,
      expected_min_messages: Number(s.expected_min_messages) || 0,
    }))
    const resp = await updateWorkflowStages({ updates })
    stages.value = (resp.data.stages || []).map((s) => ({ ...s }))
    stagesMessage.value = '已保存。仪表盘点"重算全部评分"可让历史数据生效。'
    stagesMessageType.value = 'ok'
  } catch (e) {
    stagesMessage.value = '保存失败：' + (e.response?.data?.error || e.message)
    stagesMessageType.value = 'err'
  } finally {
    stagesSaving.value = false
  }
}
</script>

<style scoped>
.settings-page { max-width: 760px; margin: 0 auto; padding: 24px; height: 100%; overflow-y: auto; }
.back-link { color: #4f7cff; text-decoration: none; font-size: 14px; }
.back-link:hover { text-decoration: underline; }
h1 { margin: 16px 0 8px; }
.hint { color: #666; font-size: 14px; margin-bottom: 16px; }
.card { background: #fff; border: 1px solid #e6e8eb; border-radius: 8px; padding: 24px; }
.form-group { margin-bottom: 18px; display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-weight: 500; font-size: 14px; color: #333; }
.form-group input[type="text"], .form-group input[type="password"], .form-group input[type="number"] {
  padding: 8px 10px; border: 1px solid #d9dde2; border-radius: 6px; font-size: 14px;
}
.form-group small { color: #888; font-size: 12px; }
.form-group small code { background: #f5f6f8; padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.checkbox-group label { display: flex; align-items: center; gap: 8px; font-weight: normal; }
.key-row { display: flex; gap: 8px; }
.key-row input { flex: 1; }
.meta { color: #888; font-size: 12px; margin: 8px 0 16px; }
.actions { display: flex; gap: 12px; margin-top: 8px; }
.btn-primary { background: #4f7cff; color: #fff; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { background: #f0f2f5; color: #333; border: 1px solid #d9dde2; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.msg { margin-top: 12px; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
.msg.ok { background: #e8f5e9; color: #2e7d32; }
.msg.err { background: #fdeaea; color: #c62828; }
.weight-warn { color: #c62828 !important; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.stages-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.stages-table th, .stages-table td { padding: 10px 8px; text-align: left; border-bottom: 1px solid #eef0f3; font-size: 14px; }
.stages-table th { color: #666; font-weight: 500; background: #fafbfc; }
.stages-table td code { background: #f5f6f8; padding: 2px 6px; border-radius: 3px; font-size: 12px; color: #555; }
.stages-table input[type="number"] { width: 100%; padding: 6px 10px; border: 1px solid #d9dde2; border-radius: 6px; font-size: 14px; }
</style>
