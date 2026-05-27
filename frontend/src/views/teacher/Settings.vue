<template>
  <div class="settings-page">
    <div class="page-header">
      <router-link to="/teacher/dashboard" class="back-link">← 返回仪表盘</router-link>
      <h1>教师设置</h1>
      <p class="page-hint">Dify 平台配置已迁移至管理员后台。如需修改请联系超级管理员。</p>
    </div>

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
          每个阶段需要的最少消息数。学生在该阶段累计消息数达到此值才会被判为"已完成"。设为 0 表示只要触达该阶段即视为完成。
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
  getScoringConfig, updateScoringConfig,
  getWorkflowStages, updateWorkflowStages,
} from '../../api/teacher'

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

function formatDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

onMounted(() => {
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
    scoringMessage.value = '已保存。'
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
const stages = ref([])

async function loadStages() {
  try {
    const resp = await getWorkflowStages()
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
    stagesMessage.value = '已保存。'
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
.settings-page { max-width: 1000px; margin: 0 auto; padding: 24px 32px 48px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 28px; }
.back-link { display: inline-block; margin-bottom: 8px; font-size: 13px; color: #4a90d9; text-decoration: none; }
.back-link:hover { text-decoration: underline; }
.page-header h1 { font-size: 24px; font-weight: 600; color: #1f2937; margin: 0; }
.page-hint { font-size: 13px; color: #6b7280; margin: 6px 0 0; }
.settings-section { margin-bottom: 28px; }
.section-head { margin-bottom: 12px; }
.section-head h2 { font-size: 16px; font-weight: 600; color: #1f2937; margin: 0 0 4px; }
.section-hint { color: #6b7280; font-size: 13px; line-height: 1.6; margin: 0; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 18px; }
.field:last-child { margin-bottom: 0; }
.field > label { font-size: 13px; font-weight: 500; color: #374151; }
.field input { width: 100%; padding: 9px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; background: #fff; color: #1f2937; }
.field input:focus { outline: none; border-color: #4a90d9; box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.15); }
.field small { color: #6b7280; font-size: 12px; line-height: 1.5; }
.field-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px 20px; margin-bottom: 18px; }
.field-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.field-grid .field { margin-bottom: 0; }
.weight-sum { font-size: 13px; color: #4b5563; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 12px; margin: 0 0 18px; }
.weight-sum strong { color: #1f2937; }
.weight-warn { background: #fef2f2 !important; border-color: #fecaca !important; color: #b91c1c !important; }
.weight-warn strong { color: #b91c1c !important; }
.meta { color: #9ca3af; font-size: 12px; margin: 4px 0 16px; padding-top: 12px; border-top: 1px dashed #e5e7eb; }
.actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 9px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: #357abd; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-secondary:hover:not(:disabled) { background: #f9fafb; }
.inline-msg { margin: 0; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
.inline-msg.ok { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.inline-msg.err { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.stages-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
.stages-table th, .stages-table td { padding: 11px 12px; text-align: left; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
.stages-table th { color: #6b7280; font-weight: 500; background: #fafbfc; border-bottom: 1px solid #e5e7eb; }
.stages-table td code { background: #f3f4f6; padding: 2px 7px; border-radius: 3px; font-size: 12px; color: #4b5563; }
.stages-table .col-num { width: 160px; text-align: right; }
.stages-table .col-num input { width: 100%; padding: 7px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; text-align: right; }
.empty-hint { color: #9ca3af; text-align: center; padding: 28px; font-size: 14px; }
.empty-hint code { background: #f3f4f6; padding: 1px 6px; border-radius: 3px; font-size: 12.5px; color: #4b5563; }
.loading-hint { color: #9ca3af; font-size: 14px; padding: 16px 0; }
</style>
