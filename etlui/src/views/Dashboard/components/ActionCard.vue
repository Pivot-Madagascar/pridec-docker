<template>
  <button
    :disabled="disabled"
    class="action-card" data-test="action-card"
    :class="{ 'card-success': action.success }"
    @click="handleClick"
  >
    <div class="card-icon" :class="action.iconClass">
      <Icon v-if="action.icon" :path="action.icon" class="icon-svg" />
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
import { computed } from 'vue'
import Icon from '@/components/Icons'

interface Action {
  key: string
  label: string
  subtitle?: string
  icon?: string
  iconClass?: string
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
@reference "tailwindcss";

.action-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
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
  background: radial-gradient(circle at top left, rgba(99, 102, 241, 0.1), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-card:hover:not(:disabled)::before {
  opacity: 1;
}

.action-card:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(99, 102, 241, 0.1);
  transform: translateY(-4px);
}

.action-card:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.action-card.card-success {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}

.card-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

/* Icon colors, set per job in src/config/pipeline.ts */
.icon-blue, .icon-indigo { background: #6366f1; }
.icon-sky { background: #0ea5e9; }
.icon-green { background: #16a34a; }
.icon-teal { background: #0d9488; }
.icon-purple { background: #8b5cf6; }
.icon-orange { background: #ea580c; }
.icon-amber { background: #d97706; }
.icon-rose { background: #e11d48; }
.icon-emerald { background: #059669; }
.icon-slate { background: #64748b; }

.icon-svg {
  width: 1.25rem;
  height: 1.25rem;
  color: white;
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
  color: #f1f5f9;
  display: block;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.card-subtitle {
  font-size: 0.8125rem;
  color: #94a3b8;
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
  color: #fbbf24;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.status-done {
  color: #34d399;
  font-weight: 600;
}

.status-pending {
  color: #64748b;
}

.status-error .status-pending {
  color: #f87171;
}

.status-inactive {
  color: #475569;
  opacity: 0.6;
}

.spinner {
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid #fbbf24;
  border-top-color: transparent;
  border-radius: 50%;
}
</style>