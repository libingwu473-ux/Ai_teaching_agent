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
    <div class="card" v-if="stageDetails.length">
      <h2>各阶段完成率</h2>
      <p class="section-hint">
        平均进度口径：所有会话在该阶段已发消息数（单会话最多按门槛计算，不超额）÷ 门槛 × 总会话数。<br />
        例：3 个会话该阶段各发 1 条、门槛 3 → 3 / (3×3) = 33.33%。门槛在"系统配置 → 阶段完成门槛"调整。
      </p>
      <p v-if="allStagesZero" class="empty-data-warn">
        所有阶段完成率均为 0 — 通常是 Dify workflow 未在 <code>node_finished</code> / <code>workflow_finished</code> 事件中输出 <code>current_stage</code>，或还没有学生在该阶段发消息。
      </p>
      <div class="stage-bars">
        <div v-for="s in stageDetails" :key="s.stage_key" class="bar-row">
          <span class="bar-label" :title="s.stage_key">{{ s.stage_name }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: (s.rate || 0) * 100 + '%' }"></div>
          </div>
          <span class="bar-value">{{ ((s.rate || 0) * 100).toFixed(2) }}%</span>
          <span class="bar-extra">
            {{ s.messages_counted }} / {{ s.messages_needed }} 条消息
            <em v-if="s.messages_actual > s.messages_counted">（实际 {{ s.messages_actual }}，超额未计）</em>
          </span>
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
  stage_completion_detail: [],
  daily_active_users: [],
})

const stageDetails = computed(() => stats.value.stage_completion_detail || [])
const allStagesZero = computed(() =>
  stageDetails.value.length > 0 &&
  stageDetails.value.every((s) => (s.rate || 0) === 0)
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
.section-hint { color: #6b7280; font-size: 12.5px; line-height: 1.6; margin: 0 0 14px; }
.bar-extra { color: #6b7280; font-size: 12px; margin-left: 12px; }
.bar-extra em { color: #9ca3af; font-style: normal; margin-left: 4px; }
</style>
