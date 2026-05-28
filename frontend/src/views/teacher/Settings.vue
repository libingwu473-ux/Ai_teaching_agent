<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">评分设置</h1>
        <p class="app-page-subtitle">调整自动评分权重和阶段完成门槛。Dify 平台配置请联系超级管理员</p>
      </div>
    </div>

    <!-- 评分参数 -->
    <el-card shadow="never" v-loading="!scoringLoaded" class="settings-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">评分参数</span>
          <span class="card-header-hint">修改后会影响后续评分；可在仪表盘点"重算全部评分"对历史会话生效</span>
        </div>
      </template>

      <el-form :model="scoringForm" label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="阶段完成度权重">
              <el-input-number v-model="scoringForm.stage_completion_weight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="流程遵循度权重">
              <el-input-number v-model="scoringForm.sequence_adherence_weight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="时间投入权重">
              <el-input-number v-model="scoringForm.time_investment_weight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="参与度权重">
              <el-input-number v-model="scoringForm.engagement_weight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-alert
          :type="weightOk ? 'success' : 'warning'"
          :closable="false"
          show-icon
          :title="`四项权重之和 = ${weightSum.toFixed(2)}（应当 ≈ 1.00）`"
          style="margin-bottom: 16px;"
        />

        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="最小会话分钟">
              <el-input-number v-model="scoringForm.min_session_minutes" :min="0" :max="120" :step="1" style="width: 100%;" />
              <div class="form-hint">会话总时长低于此值时，"时间投入"维度直接判 0。设为 0 可关闭门槛。</div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="满分">
              <el-input-number v-model="scoringForm.max_score" :min="1" :max="1000" :step="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <div v-if="scoringCurrent.updated_at" class="meta-line">
          最后修改：{{ formatDate(scoringCurrent.updated_at) }}
          <span v-if="scoringCurrent.updated_by">· 修改人：{{ scoringCurrent.updated_by }}</span>
        </div>

        <el-button type="primary" :loading="scoringSaving" :disabled="!weightOk" @click="saveScoring">保存</el-button>
        <el-button @click="loadScoring" :disabled="scoringSaving">重新加载</el-button>
      </el-form>
    </el-card>

    <!-- 阶段门槛 -->
    <el-card shadow="never" v-loading="!stagesLoaded" class="settings-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">阶段完成门槛</span>
          <span class="card-header-hint">
            每个阶段需要的最少消息数；学生在该阶段累计消息数达到此值才会被判为"已完成"。设为 0 表示触达即完成
          </span>
        </div>
      </template>

      <el-empty v-if="!stages.length" description="未找到教学流程，请先运行 python manage.py seed_workflow" />

      <el-table v-else :data="stages" style="width: 100%;" stripe>
        <el-table-column prop="name" label="阶段" min-width="160" />
        <el-table-column label="标识" min-width="180">
          <template #default="{ row }"><el-tag type="info" size="small">{{ row.stage_key }}</el-tag></template>
        </el-table-column>
        <el-table-column label="最少消息数" width="200" align="right">
          <template #default="{ row }">
            <el-input-number v-model="row.expected_min_messages" :min="0" :max="999" :step="1" controls-position="right" style="width: 140px;" />
          </template>
        </el-table-column>
      </el-table>

      <div v-if="stages.length" style="margin-top: 16px;">
        <el-button type="primary" :loading="stagesSaving" @click="saveStages">保存</el-button>
        <el-button @click="loadStages" :disabled="stagesSaving">重新加载</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getScoringConfig, updateScoringConfig,
  getWorkflowStages, updateWorkflowStages,
} from '../../api/teacher'

const scoringLoaded = ref(false)
const scoringSaving = ref(false)
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

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }

onMounted(() => { loadScoring(); loadStages() })

async function loadScoring() {
  try {
    const resp = await getScoringConfig()
    scoringCurrent.value = resp.data
    Object.assign(scoringForm, {
      stage_completion_weight: resp.data.stage_completion_weight,
      sequence_adherence_weight: resp.data.sequence_adherence_weight,
      time_investment_weight: resp.data.time_investment_weight,
      engagement_weight: resp.data.engagement_weight,
      min_session_minutes: resp.data.min_session_minutes,
      max_score: resp.data.max_score,
    })
    scoringLoaded.value = true
  } catch (e) {
    ElMessage.error('加载评分参数失败：' + (e.response?.data?.error || e.message))
  }
}

async function saveScoring() {
  scoringSaving.value = true
  try {
    const resp = await updateScoringConfig({ ...scoringForm })
    scoringCurrent.value = resp.data
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.error || e.message))
  } finally { scoringSaving.value = false }
}

const stagesLoaded = ref(false)
const stagesSaving = ref(false)
const stages = ref([])

async function loadStages() {
  try {
    const resp = await getWorkflowStages()
    stages.value = (resp.data.stages || []).map((s) => ({ ...s }))
    stagesLoaded.value = true
  } catch (e) {
    ElMessage.error('加载阶段配置失败：' + (e.response?.data?.error || e.message))
  }
}

async function saveStages() {
  stagesSaving.value = true
  try {
    const updates = stages.value.map((s) => ({
      id: s.id, expected_min_messages: Number(s.expected_min_messages) || 0,
    }))
    const resp = await updateWorkflowStages({ updates })
    stages.value = (resp.data.stages || []).map((s) => ({ ...s }))
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.error || e.message))
  } finally { stagesSaving.value = false }
}
</script>

<style scoped>
.settings-card { margin-bottom: 16px; }
.card-header { display: flex; flex-direction: column; gap: 4px; }
.card-header-title { font-size: 15px; font-weight: 600; color: var(--gray-900); }
.card-header-hint { font-size: 12px; color: var(--gray-500); line-height: 1.5; }
.form-hint { font-size: 12px; color: var(--gray-500); margin-top: 4px; line-height: 1.5; }
.meta-line { font-size: 12px; color: var(--gray-400); padding: 8px 0 16px; border-top: 1px dashed var(--gray-200); margin-top: 6px; }
</style>
