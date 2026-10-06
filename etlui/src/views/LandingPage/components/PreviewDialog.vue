<template>
  <!-- Native <dialog>: showModal() gives the backdrop, focus trap and Escape for free. -->
  <dialog
    ref="dialog"
    class="preview-dialog"
    :aria-labelledby="titleId"
    @cancel.prevent="emit('close')"
    @click.self="emit('close')"
  >
    <header class="preview-header">
      <div class="preview-heading">
        <Icon :path="ICONS.eye" class="preview-heading-icon" />
        <h3 :id="titleId" class="preview-title">{{ title }}</h3>
        <span class="preview-badge" :class="`is-${source}`">
          {{ source === 'server' ? 'On server' : 'Selected file — not uploaded' }}
        </span>
      </div>
      <button type="button" class="preview-close" aria-label="Close preview" @click="emit('close')">
        <Icon :path="ICONS.close" class="preview-close-icon" />
      </button>
    </header>

    <div class="preview-body">
      <div v-if="loading" class="preview-state" role="status">
        <span class="preview-spinner" aria-hidden="true"></span>
        Loading preview…
      </div>
      <div v-else-if="error" class="preview-state is-error" role="alert">{{ error }}</div>
      <slot v-else />
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { ref, watch, useId } from 'vue'
import Icon, { ICONS } from '@/components/Icons'

const props = defineProps<{
  open: boolean
  title: string
  source: 'server' | 'local'
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  close: []
}>()

const titleId = useId()
const dialog = ref<HTMLDialogElement>()

watch(
  () => props.open,
  (open) => {
    if (open && !dialog.value?.open) dialog.value?.showModal()
    if (!open && dialog.value?.open) dialog.value.close()
  },
  { flush: 'post' }
)
</script>

<style scoped>
@reference "tailwindcss";

.preview-dialog {
  margin: auto;
  width: min(96vw, 1600px);
  height: 90vh;
  padding: 0;
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}

.preview-dialog[open] {
  display: flex;
  flex-direction: column;
  animation: preview-in 0.15s ease-out;
}

.preview-dialog::backdrop {
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(2px);
}

@keyframes preview-in {
  from {
    opacity: 0;
    transform: translateY(0.5rem) scale(0.99);
  }
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: #1e293b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.preview-heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex-wrap: wrap;
}

.preview-heading-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #60a5fa;
}

.preview-title {
  font-family: ui-monospace, monospace;
  font-size: 1.125rem;
  font-weight: 700;
  color: #f1f5f9;
}

.preview-badge {
  padding: 0.125rem 0.625rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.preview-badge.is-server {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
}

.preview-badge.is-local {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.12);
}

.preview-close {
  display: flex;
  padding: 0.375rem;
  border-radius: 0.5rem;
  color: #94a3b8;
  cursor: pointer;
}

.preview-close:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.08);
}

.preview-close-icon {
  width: 1.25rem;
  height: 1.25rem;
}

.preview-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 1.25rem 1.5rem;
}

.preview-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  height: 100%;
  color: #94a3b8;
}

.preview-state.is-error {
  color: #f87171;
}

.preview-spinner {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid rgba(96, 165, 250, 0.3);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: preview-spin 0.8s linear infinite;
}

@keyframes preview-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
