<template>
  <BaseDialog :open="open" backdrop-close class="preview-dialog" :aria-labelledby="titleId" @dismiss="emit('close')">
    <header class="preview-header">
      <div class="preview-heading">
        <Icon :path="ICONS.eye" class="preview-heading-icon" />
        <h3 :id="titleId" class="preview-title">{{ title }}</h3>
        <span v-if="source" class="preview-badge" :class="`is-${source}`">
          {{ BADGES[source] }}
        </span>
      </div>
      <div class="preview-heading">
        <slot name="actions" />
        <Button variant="ghost" size="icon-sm" aria-label="Close preview" @click="emit('close')">
          <Icon :path="ICONS.close" class="size-5" />
        </Button>
      </div>
    </header>

    <div class="preview-body">
      <div v-if="loading" class="preview-state" role="status">
        <span class="preview-spinner animate-spin" aria-hidden="true"></span>
        {{ loadingLabel ?? 'Loading preview…' }}
      </div>
      <div v-else-if="error" class="preview-state is-error" role="alert">{{ error }}</div>
      <slot v-else />
    </div>
    <div v-if="$slots.footer" class="preview-footer" data-test="preview-footer"><slot name="footer" /></div>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useId } from 'vue'
import Icon, { ICONS } from '@/components/Icons'
import BaseDialog from './BaseDialog.vue'
import { Button } from '@/components/ui/button'

defineProps<{
  open: boolean
  title: string
  source?: 'server' | 'local' | 'default' // no badge without it (ImportAvailabilityDialog)
  loading: boolean
  error: string
  loadingLabel?: string
}>()

const emit = defineEmits<{
  close: []
}>()

const titleId = useId()
const BADGES = { server: 'On server', local: 'Selected file — not uploaded', default: 'Default file' }
</script>

<style scoped>
@reference "tailwindcss";

.preview-dialog {
  margin: auto;
  width: min(96vw, 1600px);
  height: 90vh;
  padding: 0;
  background: #0f172a;
  overflow: hidden;
}

.preview-dialog[open] {
  display: flex;
  flex-direction: column;
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

.preview-badge.is-default {
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.12);
}


.preview-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 1.25rem 1.5rem;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: #1e293b;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
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
}
</style>
