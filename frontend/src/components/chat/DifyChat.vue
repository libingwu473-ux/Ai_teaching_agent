<template>
  <div class="chat-container">
    <!-- 侧边栏：会话列表 -->
    <aside class="chat-sidebar">
      <button @click="newChat" class="new-chat-btn">+ 新建对话</button>
      <div class="conversation-list">
        <div
          v-for="conv in store.conversations"
          :key="conv.id"
          @click="selectConversation(conv)"
          :class="['conv-item', { active: conv.id === store.currentConvId }]"
        >
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <div class="conv-meta">
            <span class="conv-date">{{ formatDate(conv.updated_at) }}</span>
            <button @click.stop="handleDeleteConv(conv.id)" class="conv-delete" title="删除">×</button>
          </div>
        </div>
        <div v-if="store.conversations.length === 0" class="empty-hint">暂无对话记录</div>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <main class="chat-main">
      <!-- 阶段进度 -->
      <StageProgress
        :stages="workflowStages"
        :currentStage="store.currentStage"
        :completedStages="store.completedStages"
      />

      <!-- 消息列表 -->
      <div class="messages-area" ref="messagesRef">
        <div v-if="store.messages.length === 0 && !store.isStreaming" class="welcome-msg">
          <h2>欢迎使用 AI 教学助手</h2>
          <p>请按照教师的引导步骤进行学习</p>
        </div>

        <MessageBubble v-for="msg in store.messages" :key="msg.id" :message="msg" />

        <!-- 流式输出 -->
        <div v-if="store.isStreaming" class="message-bubble ai">
          <div class="bubble-avatar">AI</div>
          <div class="bubble-content">
            <div class="bubble-text streaming">
              {{ store.streamingText }}<span class="cursor">|</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <FileUploader @files-selected="onFilesSelected" />
        <textarea
          v-model="inputText"
          @keydown.enter.exact.prevent="sendMessage"
          placeholder="请输入你的问题..."
          :disabled="store.isStreaming"
          rows="2"
        ></textarea>
        <button
          @click="sendMessage"
          :disabled="!inputText.trim() || store.isStreaming"
          class="send-btn"
        >
          {{ store.isStreaming ? '生成中...' : '发送' }}
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useChatStore } from '../../stores/chat'
import { getChatURL } from '../../api/chat'
import MessageBubble from './MessageBubble.vue'
import StageProgress from './StageProgress.vue'
import FileUploader from './FileUploader.vue'

const route = useRoute()
const store = useChatStore()
const inputText = ref('')
const messagesRef = ref(null)
const uploadedFiles = ref([])
const abortController = ref(null)

const workflowStages = [
  { key: 'stage_concept', name: '概念讲解' },
  { key: 'stage_practice', name: '练习测验' },
  { key: 'stage_summary', name: '总结评估' },
]

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN')
}

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || store.isStreaming) return

  inputText.value = ''
  store.addMessage({ id: Date.now(), role: 'user', content: query, timestamp: new Date().toISOString() })
  store.resetStreaming()
  store.setStreaming(true)

  await nextTick()
  scrollToBottom()

  const token = localStorage.getItem('access_token')
  abortController.value = new AbortController()

  try {
    await fetchEventSource(getChatURL(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        query,
        conversation_id: getDifyConvId() || '',
      }),
      signal: abortController.value.signal,
      openWhenHidden: true,

      onmessage(event) {
        try {
          const data = JSON.parse(event.data)
          console.log('[SSE]', event.event, data.answer ? `answer:${data.answer.length}chars` : Object.keys(data).join(','))

          // chatflow 用 `message`、agent app 用 `agent_message`，都按"追加 answer 片段"处理
          if ((event.event === 'message' || event.event === 'agent_message') && data.answer) {
            store.appendStreamingText(data.answer)
            scrollToBottom()
          } else if (event.event === 'text_chunk') {
            // chatflow 的 text_chunk 形如 { data: { text: "..." } }
            const chunk =
              (data.data && typeof data.data === 'object' ? data.data.text : data.data) ||
              data.text || ''
            if (chunk) {
              store.appendStreamingText(chunk)
              scrollToBottom()
            }
          } else if (event.event === 'stage_change') {
            store.setStage(data.stage || '')
            console.log('[SSE] stage changed to', data.stage)
          } else if (event.event === 'message_end') {
            if (data.session_info) {
              store.currentConvId = data.session_info.id || store.currentConvId
              store.setCompletedStages(data.session_info.completed_stages || [])
              store.setStage(data.session_info.current_stage || '')
            }
            finishMessage()
          } else if (event.event === 'error') {
            console.error('[SSE] error event:', data)
            store.appendStreamingText(`\n[错误] ${data.message || '未知错误'}`)
            finishMessage()
          }
        } catch (e) {
          console.warn('[SSE] parse error:', e)
        }
      },

      onclose() {
        finishMessage()
      },

      onerror(err) {
        console.error('SSE error:', err)
        finishMessage()
        throw err // stop retry
      },
    })
  } catch {
    finishMessage()
  }
}

function finishMessage() {
  if (store.streamingText) {
    console.log('[SSE] finalizing message:', store.streamingText.length, 'chars')
    store.addMessage({
      id: Date.now(),
      role: 'ai',
      content: store.streamingText,
      timestamp: new Date().toISOString(),
    })
  }
  store.resetStreaming()
  // 延迟刷新会话列表，等后端写库完成
  setTimeout(() => store.loadConversations(), 500)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function getDifyConvId() {
  if (!store.currentConvId) return ''
  const conv = store.conversations.find(c => c.id === store.currentConvId)
  return conv ? conv.dify_conversation_id : ''
}

function newChat() {
  store.currentConvId = null
  store.messages = []
  store.setStage('')
  store.setCompletedStages([])
}

function selectConversation(conv) {
  store.currentConvId = conv.id
  store.loadMessages(conv.id)
}

async function handleDeleteConv(convId) {
  if (confirm('确定删除此会话？')) {
    await store.deleteConversation(convId)
    if (store.currentConvId === convId) {
      newChat()
    }
  }
}

function onFilesSelected(files) {
  uploadedFiles.value = files
}

onMounted(() => {
  store.loadConversations()
  const sessionId = route.params.sessionId
  if (sessionId) {
    store.currentConvId = sessionId
    store.loadMessages(sessionId)
  }
})

watch(() => store.currentConvId, (newId) => {
  if (newId) {
    store.loadMessages(newId)
  }
})
</script>
