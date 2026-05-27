<template>
  <div class="settings-page">
    <div class="page-header">
      <router-link to="/teacher/dashboard" class="back-link">← 返回仪表盘</router-link>
      <h1>系统配置</h1>
    </div>

    <!-- Dify 平台 -->
    <section class="settings-section">
      <div class="section-head">
        <h2>Dify 平台</h2>
        <p class="section-hint">修改后立即生效，所有用户的新对话都将使用新配置。API 密钥仅在保存时被替换 —— 留空表示不修改。</p>
      </div>

      <div class="card" v-if="loaded">
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
          <small>对应 Dify 后台的 chatflow / workflow ID（仅记录，便于追溯）。</small>
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
          <button class="btn-secondary" :disabled="saving" @click="reload">重新加载</button>
          <p v-if="message" :class="['inline-msg', messageType]">{{ message }}</p>
        </div>
      </div>
      <p v-else class="loading-hint">加载中...</p>
    </section>

    <!-- 评分参数 -->
    <section class="settings-section">
      <div class="section-head">
        <h2>评分参数</h2>
        <p class="section-hint">修改后会影响后续的评分计算；可在仪表盘点"重算全部评分"对历史会话生效。</p>
      </div>

      <div class="card" v-if="scoringLoaded">
        <div class="field-grid cols-4">
          <div class="field">
            <label>阶段完成度权重</label>
            <input v-model.number="scoringForm.stage_completion_weight" type="number" min="0" max="1" step="0.05" />
          </div>
          <div class="field">
            <label>流程遵循度权重</label>
            <input v-model.number="scoringForm.sequence_adherence_weight" type="number" min="0" max="1" step="0.05" />
          </div>
          <div class="field">
            <label>时间投入权重</label>
            <input v-model.number="scoringForm.time_investment_weight" type="number" min="0" max="1" step="0.05" />
          </div>
          <div class="field">
            <label>参与度权重</label>
            <input v-model.number="scoringForm.engagement_weight" type="number" min="0" max="1" step="0.05" />
          </div>
        </div>

        <p class="weight-sum" :class="{ 'weight-warn': !weightOk }">
          四项权重之和 = <strong>{{ weightSum.toFixed(2) }}</strong>（应当 ≈ 1.00）
        </p>

        <div class="field-grid">
          <div class="field">
            <label>最小会话分钟</label>
            <input v-model.number="scoringForm.min_session_minutes" type="number" min="0" max="120" step="1" />
            <small>会话总时长低于此值时，"时间投入"维度直接判 0。设为 0 可关闭门槛。</small>
          </div>
          <div class="field">
            <label>满分</label>
            <input v-model.number="scoringForm.max_score" type="number" min="1" max="1000" step="1" />
          </div>
          <div></div>
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
          <p v-if="scoringMessage" :class="['inline-msg', scoringMessageType]">{{ scoringMessage }}</p>
        </div>
      </div>
      <p v-else class="loading-hint">加载中...</p>
    </section>

    <!-- 阶段门槛 -->
    <section class="settings-section">
      <div class="section-head">
        <h2>阶段完成门槛</h2>
        <p class="section-hint">
          每个阶段需要的最少消息数。学生在该阶段累计消息数达到此值才会被判为"已完成"。设为 0 表示只要触达该阶段即视为完成。修改后可在仪表盘点"重算全部评分"对历史会话生效。
        </p>
      </div>

      <div class="card" v-if="stagesLoaded">
        <p v-if="!stages.length" class="empty-hint">未找到教学流程，请先运行 <code>python manage.py seed_workflow</code>。</p>

        <table v-else class="stages-table">
          <thead>
            <tr>
              <th>阶段</th>
              <th>标识</th>
              <th class="col-num">最少消息数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in stages" :key="s.id">
              <td>{{ s.name }}</td>
              <td><code>{{ s.stage_key }}</code></td>
              <td class="col-num">
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
          <p v-if="stagesMessage" :class="['inline-msg', stagesMessageType]">{{ stagesMessage }}</p>
        </div>
      </div>
      <p v-else class="loading-hint">加载中...</p>
    </section>
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
.settings-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 32px 48px;
  height: 100%;
  overflow-y: auto;
}

/* Page header */
.page-header { margin-bottom: 28px; }
.back-link {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #4a90d9;
  text-decoration: none;
}
.back-link:hover { text-decoration: underline; }
.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

/* Section */
.settings-section { margin-bottom: 28px; }
.section-head { margin-bottom: 12px; }
.section-head h2 {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px;
}
.section-hint {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

/* Card */
.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

/* Field */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
}
.field:last-child { margin-bottom: 0; }
.field > label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}
.field input[type="text"],
.field input[type="password"],
.field input[type="number"],
.field input:not([type]) {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
  color: #1f2937;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field input:focus {
  outline: none;
  border-color: #4a90d9;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.15);
}
.field small {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}
.field small code {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11.5px;
  font-family: ui-monospace, Consolas, monospace;
  color: #4b5563;
}

/* Grid for inline fields */
.field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 20px;
  margin-bottom: 18px;
}
.field-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.field-grid .field { margin-bottom: 0; }

/* Checkbox line */
.check-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
  font-weight: normal;
  padding: 8px 0;
  user-select: none;
}
.check-line input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
}

/* Key row */
.key-row { display: flex; gap: 8px; }
.key-row input { flex: 1; }

/* Weight sum */
.weight-sum {
  font-size: 13px;
  color: #4b5563;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 12px;
  margin: 0 0 18px;
}
.weight-sum strong { color: #1f2937; }
.weight-warn {
  background: #fef2f2 !important;
  border-color: #fecaca !important;
  color: #b91c1c !important;
}
.weight-warn strong { color: #b91c1c !important; }

/* Meta */
.meta {
  color: #9ca3af;
  font-size: 12px;
  margin: 4px 0 16px;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
}

/* Actions */
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.btn-primary {
  background: #4a90d9;
  color: #fff;
  border: none;
  padding: 9px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  width: auto;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-secondary {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}
.btn-secondary:hover:not(:disabled) { background: #f9fafb; }

/* Inline message after buttons */
.inline-msg {
  margin: 0;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
}
.inline-msg.ok { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.inline-msg.err { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

/* Stages table */
.stages-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
}
.stages-table th,
.stages-table td {
  padding: 11px 12px;
  text-align: left;
  border-bottom: 1px solid #f0f2f5;
  font-size: 14px;
}
.stages-table th {
  color: #6b7280;
  font-weight: 500;
  background: #fafbfc;
  border-bottom: 1px solid #e5e7eb;
}
.stages-table td code {
  background: #f3f4f6;
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 12px;
  color: #4b5563;
  font-family: ui-monospace, Consolas, monospace;
}
.stages-table .col-num { width: 160px; text-align: right; }
.stages-table .col-num input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  text-align: right;
}
.stages-table .col-num input:focus {
  outline: none;
  border-color: #4a90d9;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.15);
}

/* Hints */
.empty-hint {
  color: #9ca3af;
  text-align: center;
  padding: 28px;
  font-size: 14px;
}
.empty-hint code {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12.5px;
  color: #4b5563;
}
.loading-hint {
  color: #9ca3af;
  font-size: 14px;
  padding: 16px 0;
}

/* Responsive */
@media (max-width: 768px) {
  .settings-page { padding: 16px; }
  .field-grid,
  .field-grid.cols-4 { grid-template-columns: 1fr; }
  .actions { width: 100%; }
  .inline-msg { width: 100%; }
}
</style>
