<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <h1 class="app-page-title">教学管理仪表盘</h1>
        <p class="app-page-subtitle">学生学习概览、阶段完成情况和评分管理</p>
      </div>
      <el-button type="primary" :loading="recalculating" @click="recalcAll">
        <el-icon style="margin-right: 4px;"><Refresh /></el-icon>
        重算全部评分
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="app-stat-grid">
      <div class="app-stat-card">
        <div class="app-stat-icon" style="background: #dbeafe;"><el-icon><User /></el-icon></div>
        <div class="app-stat-label">学生总数</div>
        <div class="app-stat-value">{{ stats.total_students }}</div>
      </div>
      <div class="app-stat-card">
        <div class="app-stat-icon" style="background: #dcfce7; color: #15803d;"><el-icon><UserFilled /></el-icon></div>
        <div class="app-stat-label">活跃学生</div>
        <div class="app-stat-value">{{ stats.active_students }}</div>
      </div>
      <div class="app-stat-card">
        <div class="app-stat-icon" style="background: #fef3c7; color: #b45309;"><el-icon><DataLine /></el-icon></div>
        <div class="app-stat-label">平均评分</div>
        <div class="app-stat-value">{{ stats.average_score }}<small style="font-size: 14px; color: var(--gray-400);">分</small></div>
      </div>
      <div class="app-stat-card">
        <div class="app-stat-icon" style="background: #ede9fe; color: #6d28d9;"><el-icon><ChatDotRound /></el-icon></div>
        <div class="app-stat-label">总会话数</div>
        <div class="app-stat-value">{{ stats.total_sessions }}</div>
      </div>
    </div>

    <!-- 阶段完成率 -->
    <div v-if="stageDetails.length" class="app-card">
      <h2 class="app-card-title">各阶段完成率</h2>
      <p class="app-card-hint">
        平均进度口径：所有会话在该阶段已发消息数（单会话最多按门槛计算）÷ 门槛 × 总会话数。
        例：3 个会话该阶段各发 1 条、门槛 3 → 33.33%。门槛在"评分设置"调整。
      </p>
      <el-alert
        v-if="allStagesZero"
        title="所有阶段完成率均为 0"
        type="warning"
        :closable="false"
        show-icon
        description="通常是 Dify workflow 未在 node_finished/workflow_finished 事件中输出 current_stage，或还没学生在该阶段发消息"
        style="margin-bottom: 16px;"
      />
      <div>
        <div v-for="s in stageDetails" :key="s.stage_key" class="app-bar-row">
          <span class="app-bar-label" :title="s.stage_key">{{ s.stage_name }}</span>
          <div class="app-bar-track">
            <div class="app-bar-fill" :style="{ width: (s.rate || 0) * 100 + '%' }"></div>
          </div>
          <span class="app-bar-value">{{ ((s.rate || 0) * 100).toFixed(2) }}%</span>
          <span class="app-bar-extra">
            {{ s.messages_counted }} / {{ s.messages_needed }} 条
            <em v-if="s.messages_actual > s.messages_counted" style="color: var(--gray-400); font-style: normal;">
              （实际 {{ s.messages_actual }}）
            </em>
          </span>
        </div>
      </div>
    </div>

    <!-- 每日活跃 -->
    <div class="app-card">
      <h2 class="app-card-title">每日活跃用户（近 7 天）</h2>
      <div class="daily-chart">
        <div v-for="d in stats.daily_active_users" :key="d.date" class="daily-bar-wrap">
          <div class="daily-bar" :style="{ height: Math.max(d.count * 12, 4) + 'px' }" :title="`${d.date}: ${d.count}人`"></div>
          <span class="daily-label">{{ d.date.slice(5) }}</span>
        </div>
      </div>
    </div>

    <!-- 学生列表 -->
    <div class="app-card">
      <h2 class="app-card-title">学生列表</h2>
      <div class="app-toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索学生姓名/邮箱..."
          style="width: 280px;"
          clearable
          @input="loadStudents"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <el-table :data="students" empty-text="暂无学生" stripe style="width: 100%">
        <el-table-column label="姓名" min-width="140">
          <template #default="{ row }">{{ row.display_name || row.username }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="160" :formatter="(r) => r.email || '—'" />
        <el-table-column prop="total_sessions" label="会话数" width="90" align="center" />
        <el-table-column label="平均评分" width="110" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.average_score)">{{ row.average_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最近活跃" min-width="120">
          <template #default="{ row }">{{ formatDate(row.last_active) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <router-link :to="`/teacher/students/${row.id}`" class="app-link">详情</router-link>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStudents, getStats, recalculateAllScores } from '../../api/teacher'

const searchQuery = ref('')
const students = ref([])
const recalculating = ref(false)
const stats = ref({
  total_students: 0, active_students: 0, total_sessions: 0, average_score: 0,
  stage_completion_rate: {}, stage_completion_detail: [], daily_active_users: [],
})

const stageDetails = computed(() => stats.value.stage_completion_detail || [])
const allStagesZero = computed(() =>
  stageDetails.value.length > 0 && stageDetails.value.every((s) => (s.rate || 0) === 0)
)

function formatDate(s) { return s ? new Date(s).toLocaleDateString('zh-CN') : '--' }
function scoreClass(s) {
  if (s >= 90) return 'score-excellent'
  if (s >= 75) return 'score-good'
  if (s >= 60) return 'score-pass'
  return 'score-fail'
}

async function loadStudents() {
  try {
    const resp = await getStudents({ search: searchQuery.value })
    students.value = resp.data.data || []
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
}
async function loadStats() {
  try {
    const resp = await getStats()
    stats.value = resp.data
  } catch (e) { /* ignore */ }
}

async function recalcAll() {
  try {
    await ElMessageBox.confirm('将对当前所有会话重新计算自动评分，可能需要几秒钟。继续？', '重算确认', { type: 'warning' })
    recalculating.value = true
    const resp = await recalculateAllScores()
    const d = resp.data
    ElMessage.success(`已处理 ${d.processed} 条 / 跳过 ${d.skipped} 条 / 失败 ${d.failed} 条`)
    await loadStats()
    await loadStudents()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('重算失败：' + (e.response?.data?.error || e.message))
  } finally {
    recalculating.value = false
  }
}

onMounted(() => { loadStats(); loadStudents() })
</script>
