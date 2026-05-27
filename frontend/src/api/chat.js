import client from './client'

// SSE 流式端点直连 Django（绕过 Vite 代理的缓冲，确保 SSE 实时推送）
const SSE_BASE = 'http://127.0.0.1:8000/api'

export function getChatURL() {
  return `${SSE_BASE}/chat/send/`
}

export function getConversations() {
  return client.get('/chat/conversations/')
}

export function getConversationMessages(convId) {
  return client.get(`/chat/conversations/${convId}/messages/`)
}

export function deleteConversation(convId) {
  return client.delete(`/chat/conversations/${convId}/delete/`)
}

export function uploadFile(formData) {
  return client.post('/chat/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function stopChat(taskId) {
  return client.post('/chat/stop/', { task_id: taskId })
}

export function triggerSync() {
  return client.post('/chat/sync/')
}
