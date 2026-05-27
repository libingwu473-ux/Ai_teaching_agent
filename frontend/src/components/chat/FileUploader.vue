<template>
  <div class="file-uploader">
    <label class="upload-btn" title="上传文件">
      📎
      <input type="file" @change="handleFileSelect" multiple hidden accept="image/*,.pdf,.doc,.docx,.txt,.md" />
    </label>
    <div class="file-list" v-if="files.length > 0">
      <span v-for="(file, idx) in files" :key="idx" class="file-tag">
        {{ file.name }}
        <button @click="removeFile(idx)" class="remove-file">&times;</button>
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const files = ref([])
const emit = defineEmits(['files-selected'])

function handleFileSelect(e) {
  const selected = Array.from(e.target.files)
  files.value.push(...selected)
  emit('files-selected', files.value)
}

function removeFile(idx) {
  files.value.splice(idx, 1)
  emit('files-selected', files.value)
}
</script>
