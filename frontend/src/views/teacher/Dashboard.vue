<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>教学管理仪表盘</h1>
      <button class="btn-recalc" :disabled="recalculating" @click="recalcAll">
        {{ recalculating ? '重算中...' : '重算全部评分' }}
      </button>
    </div>
    <p v-if="recalcMsg" :class="['recalc-msg', recalcMsgType]">{{ recalcMsg }}</p>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-num">{{ stats.total_students }}</span>
        <span class="stat-label">学生总数</span>
      </div>
      <div class="stat-card">
        <span class="stat-num">{{ stats.active_students }}</span>
        <span class="stat-label">活跃学生</span>
      </div>
      <div class="stat-card">
        <span class="stat-num">{{ stats.average_score }}%</span>
        <span class="stat-label">平均评分</span>
      </div>
      <div class="stat-card">
        <span class="stat-num">{{ stats.total_sessions }}</span>
        <span class="stat-label">总会话数</span>
      </div>
    </div>

    <!-- 阶段完成率 -->
    <div class="card" v-if="stageKeys.length">
      <h2>各阶段完成率</h2>
      <p v-if="allStagesZero" class="empty-data-warn">
        所有阶段完成率均为 0 — 通常是 Dify workflow 未在 <code>node_finished</code> / <code>workflow_finished</code> 事件中输出 <code>current_stage</code>。请检查 Dify 工作流配置。
      </p>
      <div class="stage-bars">
        <div v-for="key in stageKeys" :key="key" class="bar-row">
          <span class="bar-label">{{ key }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: (stats.stage_completion_rate?.[key] || 0) * 100 + '%' }"></div>
          </div>
          <span class="bar-value">{{ Math.round((stats.stage_completion_rate?.[key] || 0) * 100) }}%</span>
        </div>
      </div>
    </div>

    <!-- 每日活跃 -->
    <div class="card">
      <h2>每日活跃用户（近7天）</h2>
      <div class="daily-chart">
        <div v-for="d in stats.daily_active_users" :key="d.date" class="daily-bar-wrap">
          <div class="daily-bar" :style="{ height: Math.max(d.count * 10, 2) + 'px' }" :title="`${d.date}: ${d.count}人`"></div>
          <span class="daily-label">{{ d.date.slice(5) }}</span>
        </div>
      </div>
    </div>

    <!-- 学生列表 -->
    <div class="card">
      <h2>学生列表</h2>
      <div class="search-bar">
        <input v-model="searchQuery" @input="loadStudents" placeholder="搜索学生姓名/邮箱..." />
      </div>
      <table class="data-table" v-if="students.length">
        <thead>
          <tr>
            <th>姓名</th>
            <th>邮箱</th>
            <th>会话数</th>
            <th>平均评分</th>
            <th>最近活跃</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in students" :key="s.id">
            <td>{{ s.display_name || s.username }}</td>
            <td>{{ s.email }}</td>
            <td>{{ s.total_sessions }}</td>
            <td :class="scoreClass(s.average_score)">{{ s.average_score }}</td>
            <td>{{ formatDate(s.last_active) }}</td>
            <td>
              <router-link :to="`/teacher/students/${s.id}`" class="btn-link">详情</router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-hint">暂无学生数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStudents, getStats, recalculateAllScores } from '../../api/teacher'

const searchQuery = ref('')
const students = ref([])
const recalculating = ref(false)
const recalcMsg = ref('')
const recalcMsgType = ref('ok')
const stats = ref({
  total_students: 0,
  active_students: 0,
  total_sessions: 0,
  average_score: 0,
  stage_completion_rate: {},
  daily_active_users: [],
})

const stageKeys = computed(() => Object.keys(stats.value.stage_completion_rate || {}))
const allStagesZero = computed(() =>
  stageKeys.value.length > 0 &&
  stageKeys.value.every((k) => (stats.value.stage_completion_rate?.[k] || 0) === 0)
)

function formatDate(dateStr) {
  if (!dateStr) return '--'
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN')
}

function scoreClass(score) {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

async function loadStudents() {
  try {
    const resp = await getStudents({ search: searchQuery.value })
    students.value = resp.data.data || []
  } catch { /* ignore */ }
}

async function loadStats() {
  try {
    const resp = await getStats()
    stats.value = resp.data
  } catch { /* ignore */ }
}

async function recalcAll() {
  if (!confirm('将对当前所有会话重新计算自动评分，可能需要几秒钟。继续？')) return
  recalculating.value = true
  recalcMsg.value = ''
  try {
    const resp = await recalculateAllScores()
    const d = resp.data
    recalcMsg.value = `已处理 ${d.processed} 条 / 跳过 ${d.skipped} 条 / 失败 ${d.failed} 条`
    recalcMsgType.value = d.failed > 0 ? 'warn' : 'ok'
    await loadStats()
    await loadStudents()
  } catch (e) {
    recalcMsg.value = '重算失败：' + (e.response?.data?.error || e.message)
    recalcMsgType.value = 'err'
  } finally {
    recalculating.value = false
  }
}

onMounted(() => {
  loadStats()
  loadStudents()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; }
.btn-recalc {
  background: #4f7cff; color: #fff; border: none; padding: 8px 16px;
  border-radius: 6px; cursor: pointer; font-size: 14px;
}
.btn-recalc:disabled { opacity: 0.6; cursor: not-allowed; }
.recalc-msg { padding: 8px 12px; border-radius: 6px; margin: 8px 0; font-size: 14px; }
.recalc-msg.ok { background: #e8f5e9; color: #2e7d32; }
.recalc-msg.warn { background: #fff8e1; color: #b26500; }
.recalc-msg.err { background: #fdeaea; color: #c62828; }
</style>
