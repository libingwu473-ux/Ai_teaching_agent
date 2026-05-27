<template>
  <div class="detail-page">
    <router-link to="/teacher/dashboard" class="back-link">&larr; 返回仪表盘</router-link>
    <h1>学生学习详情</h1>

    <!-- 会话列表 -->
    <div class="card">
      <h2>学习会话</h2>
      <table class="data-table" v-if="sessions.length">
        <thead>
          <tr>
            <th>标题</th>
            <th>状态</th>
            <th>当前阶段</th>
            <th>消息数</th>
            <th>Token用量</th>
            <th>开始时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.id">
            <td>{{ s.title || '未命名' }}</td>
            <td><span :class="`status-${s.status}`">{{ statusMap[s.status] }}</span></td>
            <td>{{ s.current_stage || '--' }}</td>
            <td>{{ s.total_messages }}</td>
            <td>{{ s.total_tokens }}</td>
            <td>{{ formatDate(s.started_at) }}</td>
            <td>
              <button @click="triggerScoring(s.id)" class="btn-link">评分</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-hint">暂无会话数据</p>
    </div>

    <!-- 评分列表 -->
    <div class="card">
      <h2>评分记录</h2>
      <table class="data-table" v-if="scores.length">
        <thead>
          <tr>
            <th>会话</th>
            <th>阶段完成度</th>
            <th>流程遵循度</th>
            <th>时间投入</th>
            <th>参与度</th>
            <th>自动总分</th>
            <th>教师评分</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="sc in scores" :key="sc.id">
            <td>{{ sc.session_title }}</td>
            <td>{{ sc.auto_stage_completion }}</td>
            <td>{{ sc.auto_sequence_score }}</td>
            <td>{{ sc.auto_time_score }}</td>
            <td>{{ sc.auto_engagement_score }}</td>
            <td :class="scoreClass(sc.auto_total_score)">{{ sc.auto_total_score }}</td>
            <td>{{ sc.teacher_score ?? '--' }}</td>
            <td>{{ scoreStatusMap[sc.status] || sc.status }}</td>
            <td>
              <router-link :to="`/teacher/scores/${sc.id}`" class="btn-link">复核</router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-hint">暂无评分数据，请先对会话执行评分</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getStudentSessions, getStudentScores, triggerScoring as triggerScoringApi } from '../../api/teacher'

const route = useRoute()
const studentId = route.params.id
const sessions = ref([])
const scores = ref([])

const statusMap = { active: '进行中', completed: '已完成', abandoned: '已放弃' }
const scoreStatusMap = { pending_review: '待复核', reviewed: '已复核', finalized: '已确认' }

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '--' }
function scoreClass(s) { return s >= 90 ? 'score-excellent' : s >= 75 ? 'score-good' : s >= 60 ? 'score-pass' : 'score-fail' }

async function loadData() {
  try {
    const [sResp, scResp] = await Promise.all([
      getStudentSessions(studentId),
      getStudentScores(studentId),
    ])
    sessions.value = sResp.data.data || []
    scores.value = scResp.data.data || []
  } catch { /* ignore */ }
}

async function triggerScoring(sessionId) {
  try {
    await triggerScoringApi(sessionId)
    alert('评分完成')
    loadData()
  } catch (e) {
    alert('评分失败: ' + (e.response?.data?.error || e.message))
  }
}

onMounted(loadData)
</script>
