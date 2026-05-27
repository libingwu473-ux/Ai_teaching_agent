<template>
  <div class="detail-page">
    <router-link to="/teacher/dashboard" class="back-link">&larr; 返回仪表盘</router-link>
    <h1>评分复核</h1>

    <div class="card" v-if="score">
      <h2>自动评分结果</h2>
      <div class="score-summary">
        <div class="score-total" :class="scoreClass(score.auto_total_score)">
          <span class="big-score">{{ score.auto_total_score }}</span>
          <span>自动总分</span>
        </div>
        <div class="score-breakdown">
          <div class="score-item">阶段完成度: <strong>{{ score.auto_stage_completion }}</strong></div>
          <div class="score-item">流程遵循度: <strong>{{ score.auto_sequence_score }}</strong></div>
          <div class="score-item">时间投入: <strong>{{ score.auto_time_score }}</strong></div>
          <div class="score-item">参与度: <strong>{{ score.auto_engagement_score }}</strong></div>
        </div>
      </div>

      <!-- 阶段明细 -->
      <h3>阶段明细</h3>
      <table class="data-table" v-if="score.details?.length">
        <thead>
          <tr>
            <th>阶段</th>
            <th>完成状态</th>
            <th>消息数</th>
            <th>耗时(秒)</th>
            <th>阶段得分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in score.details" :key="d.id">
            <td>{{ d.stage_name }} ({{ d.stage_key }})</td>
            <td>{{ d.is_completed ? '✅ 完成' : '❌ 未完成' }}</td>
            <td>{{ d.message_count }}</td>
            <td>{{ d.time_spent_seconds }}</td>
            <td>{{ d.stage_score }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 教师人工评分 -->
      <h3>教师评分</h3>
      <div class="teacher-review">
        <div class="form-group">
          <label>评分 (0-100)</label>
          <input v-model.number="reviewForm.teacher_score" type="number" min="0" max="100" />
        </div>
        <div class="form-group">
          <label>评语</label>
          <textarea v-model="reviewForm.teacher_comment" rows="3" placeholder="输入评语..."></textarea>
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model="reviewForm.status">
            <option value="pending_review">待复核</option>
            <option value="reviewed">已复核</option>
            <option value="finalized">已确认</option>
          </select>
        </div>
        <p v-if="reviewError" class="error-msg">{{ reviewError }}</p>
        <button @click="submitReview" :disabled="reviewing" class="btn-primary">
          {{ reviewing ? '提交中...' : '提交审核' }}
        </button>
      </div>
    </div>

    <p v-else class="loading-hint">加载中...</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getScoreDetail, updateScore } from '../../api/teacher'

const route = useRoute()
const scoreId = route.params.id
const score = ref(null)
const reviewing = ref(false)
const reviewError = ref('')

const reviewForm = ref({
  teacher_score: 0,
  teacher_comment: '',
  status: 'reviewed',
})

function scoreClass(s) { return s >= 90 ? 'score-excellent' : s >= 75 ? 'score-good' : s >= 60 ? 'score-pass' : 'score-fail' }

async function loadScore() {
  try {
    const resp = await getScoreDetail(scoreId)
    score.value = resp.data
    reviewForm.value = {
      teacher_score: resp.data.teacher_score || resp.data.auto_total_score,
      teacher_comment: resp.data.teacher_comment || '',
      status: resp.data.status || 'reviewed',
    }
  } catch {
    score.value = null
  }
}

async function submitReview() {
  reviewing.value = true
  reviewError.value = ''
  try {
    await updateScore(scoreId, reviewForm.value)
    alert('提交成功')
    loadScore()
  } catch (e) {
    reviewError.value = e.response?.data?.error || '提交失败'
  } finally {
    reviewing.value = false
  }
}

onMounted(loadScore)
</script>
