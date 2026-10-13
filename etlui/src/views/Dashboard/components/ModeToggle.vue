<template>
  <!-- Before step 1: the mode applies to the whole cycle (DRYRUN on the server). -->
  <section class="mode-toggle" :class="{ 'is-test': dryRun }">
    <div class="mode-text">
      <span class="mode-label">Test mode</span>
      <span class="mode-hint">
        <template v-if="dryRun">DRYRUN on: nothing is written to DHIS2, the checkpoints live in Redis only.</template>
        <template v-else>Production: jobs write to DHIS2.</template>
      </span>
    </div>
    <div class="mode-buttons" role="group" aria-label="Test mode">
      <button type="button" :class="['mode-btn', { active: dryRun === false }]" :disabled="disabled || dryRun === false" @click="emit('change', false)">
        NO
      </button>
      <button type="button" :class="['mode-btn', { active: dryRun === true }]" :disabled="disabled || dryRun === true" @click="emit('change', true)">
        YES
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  dryRun: boolean | undefined // unknown until the first read of the state
  disabled?: boolean
}>()

const emit = defineEmits<{
  change: [dryRun: boolean]
}>()
</script>

<style scoped>
@reference "tailwindcss";

.mode-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  border-radius: 0.75rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mode-toggle.is-test {
  border-color: rgba(251, 191, 36, 0.5);
  background: rgba(251, 191, 36, 0.08);
}

.mode-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.mode-label {
  font-weight: 700;
  color: #f1f5f9;
}

.mode-hint {
  font-size: 0.8125rem;
  color: #94a3b8;
}

.mode-buttons {
  display: flex;
  gap: 0.5rem;
}

.mode-btn {
  padding: 0.375rem 0.875rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.mode-btn.active {
  color: #0f172a;
  background: #fbbf24;
  border-color: #fbbf24;
}

.mode-btn:disabled:not(.active) {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
