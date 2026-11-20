<template>
  <button
    :disabled="disabled"
    class="action-card" data-test="action-card"
    :data-item="action.key"
    :class="{ 'card-success': action.success }"
    @click="handleClick"
  >
    <div class="card-icon">
      <component :is="action.icon" v-if="action.icon" class="icon-svg" />
    </div>
    <div class="card-content">
      <span class="card-title">{{ action.label }}</span>
      <span v-if="action.subtitle" class="card-subtitle">{{ action.subtitle }}</span>
      <span v-if="action.statusText" class="card-status" :class="action.statusClass">
        <span v-if="action.loading" class="status-running">
          <span class="spinner animate-spin"></span>
          {{ action.statusText }}
        </span>
        <span v-else-if="action.success" class="status-done">{{ action.statusText }}</span>
        <span v-else class="status-pending">{{ action.statusText }}</span>
      </span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

interface Action {
  key: string
  label: string
  subtitle?: string
  icon?: Component
  inactive?: boolean
  loading?: boolean
  success?: boolean
  statusText?: string
  statusClass?: string
}

const props = defineProps<{
  action: Action
}>()

const emit = defineEmits<{
  'action-click': [key: string]
}>()

const disabled = computed(() => props.action.loading || props.action.inactive)

const handleClick = () => {
  emit('action-click', props.action.key)
}
</script>

<style scoped>
@reference "../../../styles/base.css";

.action-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: var(--muted);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  text-align: left;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.action-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top left, color-mix(in oklab, var(--primary) 10%, transparent), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-card:hover:not(:disabled)::before {
  opacity: 1;
}

.action-card:hover:not(:disabled) {
  border-color: color-mix(in oklab, var(--primary) 50%, transparent);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2), 0 0 0 1px color-mix(in oklab, var(--primary) 10%, transparent);
  transform: translateY(-4px);
}

.action-card:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.action-card.card-success {
  border-color: var(--success);
  background: color-mix(in oklab, var(--success) 15%, transparent);
  box-shadow: 0 0 15px color-mix(in oklab, var(--success) 20%, transparent);
}

.card-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--primary);
}

.icon-svg {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--primary-foreground);
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.card-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--foreground);
  display: block;
}

.card-subtitle {
  font-size: 0.8125rem;
  color: var(--muted-foreground);
  display: block;
}

.card-status {
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  margin-top: 0.25rem;
}

.status-running {
  color: var(--warning);
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.status-done {
  color: var(--success);
  font-weight: 600;
}

.status-pending {
  color: var(--muted-foreground);
}

.status-error .status-pending {
  color: var(--destructive);
}

.status-inactive {
  color: var(--muted-foreground);
  opacity: 0.6;
}

.spinner {
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid var(--warning);
  border-top-color: transparent;
  border-radius: 50%;
}
</style>