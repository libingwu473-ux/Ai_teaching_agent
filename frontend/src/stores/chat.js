import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConversations, getConversationMessages, deleteConversation as delConv } from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const currentConvId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)
  const streamingText = ref('')
  const currentStage = ref('')
  const completedStages = ref([])

  async function loadConversations() {
    try {
      const resp = await getConversations()
      conversations.value = resp.data.data || []
    } catch { /* ignore */ }
  }

  async function loadMessages(sessionId) {
    try {
      const resp = await getConversationMessages(sessionId)
      const raw = resp.data.data || []
      messages.value = raw.map((log) => ({
        id: log.id,
        role: 'user',
        content: log.query_text,
        timestamp: log.created_at,
      })).concat(raw.map((log) => ({
        id: log.id + '_ai',
        role: 'ai',
        content: log.answer_text,
        stage: log.stage_key,
        timestamp: log.created_at,
      }))).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    } catch { /* ignore */ }
  }

  async function deleteConversation(convId) {
    try {
      await delConv(convId)
      conversations.value = conversations.value.filter((c) => c.id !== convId)
    } catch { /* ignore */ }
  }

  function addMessage(msg) {
    messages.value.push(msg)
  }

  function setStreaming(val) {
    isStreaming.value = val
  }

  function appendStreamingText(text) {
    streamingText.value += text
  }

  function resetStreaming() {
    streamingText.value = ''
    isStreaming.value = false
  }

  function setStage(stage) {
    currentStage.value = stage
  }

  function setCompletedStages(stages) {
    completedStages.value = stages
  }

  function reset() {
    conversations.value = []
    currentConvId.value = null
    messages.value = []
    isStreaming.value = false
    streamingText.value = ''
    currentStage.value = ''
    completedStages.value = []
  }

  return {
    conversations, currentConvId, messages, isStreaming, streamingText,
    currentStage, completedStages,
    loadConversations, loadMessages, deleteConversation,
    addMessage, setStreaming, appendStreamingText, resetStreaming,
    setStage, setCompletedStages, reset,
  }
})
