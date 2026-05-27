<template>
  <div class="stage-progress" v-if="stages.length > 0">
    <div class="stage-steps">
      <div
        v-for="(stage, idx) in stages"
        :key="stage.key"
        :class="['stage-step', {
          completed: completedStages.includes(stage.key),
          active: stage.key === currentStage,
        }]"
      >
        <span class="step-dot">{{ completedStages.includes(stage.key) ? '✓' : idx + 1 }}</span>
        <span class="step-name">{{ stage.name }}</span>
        <span v-if="idx < stages.length - 1" class="step-line"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stages: { type: Array, default: () => [] },
  currentStage: { type: String, default: '' },
  completedStages: { type: Array, default: () => [] },
})
</script>
