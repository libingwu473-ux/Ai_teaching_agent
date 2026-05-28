<template>
  <div class="app-page">
    <div class="app-page-header">
      <div>
        <el-breadcrumb separator="/" style="margin-bottom: 8px;">
          <el-breadcrumb-item :to="{ path: '/teacher/dashboard' }">仪表盘</el-breadcrumb-item>
          <el-breadcrumb-item>评分复核</el-breadcrumb-item>
        </el-breadcrumb>
        <h1 class="app-page-title">评分复核</h1>
      </div>
    </div>

    <el-card v-if="score" shadow="never" class="app-card" style="margin-bottom: 16px;">
      <template #header>
        <span style="font-size: 15px; font-weight: 600; color: var(--gray-900);">自动评分结果</span>
      </template>
      <div class="score-summary-modern">
        <div class="score-total" :class="scoreClass(score.auto_total_score)">
          <div class="big-score">{{ score.auto_total_score }}</div>
          <div style="font-size: 12px;">自动总分</div>
        </div>
        <div style="flex: 1;">
          <div class="score-grid">
            <div class="score-cell">
              <span class="score-cell-label">阶段完成度</span>
              <span class="score-cell-value">{{ score.auto_stage_completion }}</span>
            </div>
            <div class="score-cell">
              <span class="score-cell-label">流程遵循度</span>
              <span class="score-cell-value">{{ score.auto_sequence_score }}</span>
            </div>
            <div class="score-cell">
              <span class="score-cell-label">时间投入</span>
              <span class="score-cell-value">{{ score.auto_time_score }}</span>
            </div>
            <div class="score-cell">
              <span class="score-cell-label">参与度</span>
              <span class="score-cell-value">{{ score.auto_engagement_score }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="score?.details?.length" shadow="never" class="app-card" style="margin-bottom: 16px;">
      <template #header>
        <span style="font-size: 15px; font-weight: 600; color: var(--gray-900);">阶段明细</span>
      </template>
      <el-table :data="score.details" stripe style="width: 100%">
        <el-table-column label="阶段" min-width="180">
          <template #default="{ row }">
            {{ row.stage_name }}
            <el-tag size="small" type="info" style="margin-left: 6px;">{{ row.stage_key }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="完成状态" width="120" align="center">
          <template #default="{ row }">
            <span :class="['app-badge', row.is_completed ? 'is-success' : 'is-gray']">
              {{ row.is_completed ? '已完成' : '未完成' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="message_count" label="消息数" width="100" align="center" />
        <el-table-column prop="time_spent_seconds" label="耗时(秒)" width="110" align="center" />
        <el-table-column prop="stage_score" label="阶段得分" width="100" align="center" />
      </el-table>
    </el-card>

    <el-card v-if="score" shadow="never" class="app-card">
      <template #header>
        <span style="font-size: 15px; font-weight: 600; color: var(--gray-900);">教师评分</span>
      </template>
      <el-form :model="reviewForm" label-width="80px" style="max-width: 480px;">
        <el-form-item label="评分">
          <el-input-number v-model="reviewForm.teacher_score" :min="0" :max="100" :step="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="评语">
          <el-input v-model="reviewForm.teacher_comment" type="textarea" :rows="3" placeholder="输入评语..." />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="reviewForm.status" style="width: 100%;">
            <el-option value="pending_review" label="待复核" />
            <el-option value="reviewed" label="已复核" />
            <el-option value="finalized" label="已确认" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="reviewing" @click="submitReview">提交审核</el-button>
      </el-form>
    </el-card>

    <el-empty v-else description="加载中..." />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getScoreDetail, updateScore } from '../../api/teacher'

const route = useRoute()
const scoreId = route.params.id
const score = ref(null)
const reviewing = ref(false)

const reviewForm = ref({ teacher_score: 0, teacher_comment: '', status: 'reviewed' })

function scoreClass(s) { return s >= 90 ? 'is-excellent' : s >= 75 ? 'is-good' : s >= 60 ? 'is-pass' : 'is-fail' }

async function loadScore() {
  try {
    const resp = await getScoreDetail(scoreId)
    score.value = resp.data
    reviewForm.value = {
      teacher_score: resp.data.teacher_score || resp.data.auto_total_score,
      teacher_comment: resp.data.teacher_comment || '',
      status: resp.data.status || 'reviewed',
    }
  } catch { score.value = null }
}

async function submitReview() {
  reviewing.value = true
  try {
    await updateScore(scoreId, reviewForm.value)
    ElMessage.success('提交成功')
    loadScore()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '提交失败')
  } finally { reviewing.value = false }
}

onMounted(loadScore)
</script>

<style scoped>
.score-summary-modern { display: flex; gap: 24px; align-items: center; }
.score-total {
  text-align: center; padding: 20px 28px; border-radius: var(--radius-lg);
  min-width: 140px; background: var(--brand-50);
  border: 1px solid var(--brand-100);
}
.score-total .big-score {
  font-size: 42px; font-weight: 700;
  color: var(--brand-700); letter-spacing: -0.02em; line-height: 1.1;
  margin-bottom: 4px;
}
.score-total.is-excellent { background: #dcfce7; border-color: #bbf7d0; }
.score-total.is-excellent .big-score { color: #166534; }
.score-total.is-good { background: var(--brand-50); border-color: var(--brand-100); }
.score-total.is-good .big-score { color: var(--brand-700); }
.score-total.is-pass { background: #fef3c7; border-color: #fde68a; }
.score-total.is-pass .big-score { color: #92400e; }
.score-total.is-fail { background: #fee2e2; border-color: #fecaca; }
.score-total.is-fail .big-score { color: #991b1b; }

.score-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.score-cell {
  background: var(--gray-50);
  padding: 12px 16px;
  border-radius: var(--radius-md);
  display: flex; flex-direction: column; gap: 4px;
}
.score-cell-label { font-size: 12px; color: var(--gray-500); }
.score-cell-value { font-size: 20px; font-weight: 600; color: var(--gray-900); }
</style>
