import client from './client'

export function getStudents(params = {}) {
  return client.get('/teacher/students/', { params })
}

export function getStudentSessions(studentId) {
  return client.get(`/teacher/students/${studentId}/sessions/`)
}

export function getStudentScores(studentId) {
  return client.get(`/teacher/students/${studentId}/scores/`)
}

export function getScoreDetail(scoreId) {
  return client.get(`/teacher/scores/${scoreId}/`)
}

export function updateScore(scoreId, data) {
  return client.put(`/teacher/scores/${scoreId}/`, data)
}

export function getStats() {
  return client.get('/teacher/stats/')
}

export function triggerScoring(sessionId) {
  return client.post('/teacher/scoring/trigger/', { session_id: sessionId })
}

export function recalculateAllScores() {
  return client.post('/teacher/scoring/recalculate-all/')
}

export function getScoringConfig() {
  return client.get('/teacher/scoring-config/')
}

export function updateScoringConfig(payload) {
  return client.put('/teacher/scoring-config/', payload)
}

export function getDifyConfig(reveal = false) {
  return client.get('/teacher/dify-config/', { params: reveal ? { reveal: 1 } : {} })
}

export function updateDifyConfig(payload) {
  return client.put('/teacher/dify-config/', payload)
}

export function getWorkflowStages() {
  return client.get('/teacher/workflow-stages/')
}

export function updateWorkflowStages(payload) {
  return client.put('/teacher/workflow-stages/', payload)
}
