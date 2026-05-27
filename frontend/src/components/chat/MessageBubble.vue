<template>
  <div :class="['message-bubble', message.role]">
    <div class="bubble-avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
    <div class="bubble-content">
      <div class="bubble-text" v-html="renderedContent"></div>
      <div class="bubble-meta" v-if="message.stage">
        <span class="stage-tag">{{ message.stage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
})

const renderedContent = computed(() => {
  // 简单的 markdown 换行渲染
  return props.message.content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
})
</script>
