<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <el-breadcrumb separator="/" style="margin-bottom: 8px;">
          <el-breadcrumb-item :to="{ path: '/teacher/dashboard' }">仪表盘</el-breadcrumb-item>
          <el-breadcrumb-item>学生学习详情</el-breadcrumb-item>
        </el-breadcrumb>
        <h1 class="app-page-title">学生学习详情</h1>
      </div>
    </div>

    <div class="app-card">
      <h2 class="app-card-title">学习会话</h2>
      <el-table :data="sessions" empty-text="暂无会话数据" stripe style="width: 100%">
        <el-table-column label="标题" min-width="200" :formatter="(r) => r.title || '未命名'" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', statusBadge(row.status)]">{{ statusMap[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="current_stage" label="当前阶段" min-width="140" :formatter="(r) => r.current_stage || '—'" />
        <el-table-column prop="total_messages" label="消息数" width="90" align="center" />
        <el-table-column prop="total_tokens" label="Token 用量" width="110" align="center" />
        <el-table-column label="开始时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="triggerScoring(row.id)">评分</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="app-card">
      <h2 class="app-card-title">评分记录</h2>
      <el-table :data="scores" empty-text="暂无评分数据，请先对会话执行评分" stripe style="width: 100%">
        <el-table-column prop="session_title" label="会话" min-width="180" />
        <el-table-column prop="auto_stage_completion" label="阶段完成度" width="110" align="center" />
        <el-table-column prop="auto_sequence_score" label="流程遵循度" width="110" align="center" />
        <el-table-column prop="auto_time_score" label="时间投入" width="100" align="center" />
        <el-table-column prop="auto_engagement_score" label="参与度" width="90" align="center" />
        <el-table-column label="自动总分" width="100" align="center">
          <template #default="{ row }">
            <strong :class="scoreClass(row.auto_total_score)">{{ row.auto_total_score }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="教师评分" width="100" align="center">
          <template #default="{ row }">{{ row.teacher_score ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', scoreStatusBadge(row.status)]">{{ scoreStatusMap[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <router-link :to="`/teacher/scores/${row.id}`" class="app-link">复核</router-link>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getStudentSessions, getStudentScores, triggerScoring as triggerScoringApi } from '../../api/teacher'

const route = useRoute()
const studentId = route.params.id
const sessions = ref([])
const scores = ref([])

const statusMap = { active: '进行中', completed: '已完成', abandoned: '已放弃' }
const scoreStatusMap = { pending_review: '待复核', reviewed: '已复核', finalized: '已确认' }

function statusBadge(s) {
  return ({ active: 'is-info', completed: 'is-success', abandoned: 'is-gray' })[s] || 'is-gray'
}
function scoreStatusBadge(s) {
  return ({ pending_review: 'is-warning', reviewed: 'is-info', finalized: 'is-success' })[s] || 'is-gray'
}
function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
function scoreClass(s) { return s >= 90 ? 'score-excellent' : s >= 75 ? 'score-good' : s >= 60 ? 'score-pass' : 'score-fail' }

async function loadData() {
  try {
    const [sResp, scResp] = await Promise.all([
      getStudentSessions(studentId), getStudentScores(studentId),
    ])
    sessions.value = sResp.data.data || []
    scores.value = scResp.data.data || []
  } catch (e) { ElMessage.error(e.response?.data?.error || e.message) }
}

async function triggerScoring(sessionId) {
  try {
    await triggerScoringApi(sessionId)
    ElMessage.success('评分完成')
    loadData()
  } catch (e) { ElMessage.error('评分失败: ' + (e.response?.data?.error || e.message)) }
}

onMounted(loadData)
</script>
