<template>
  <BaseDialog :open="open" backdrop-close class="confirm-dialog" :aria-labelledby="titleId" @dismiss="!busy && emit('cancel')">
    <div class="confirm-body">
      <div class="confirm-icon">
        <Icon :path="ICONS.reset" class="icon-svg" />
      </div>
      <div>
        <h3 :id="titleId" class="confirm-title">{{ title }}</h3>
        <p class="confirm-message"><slot /></p>
      </div>
    </div>
    <div class="confirm-actions">
      <button type="button" class="confirm-btn" :disabled="busy" autofocus @click="emit('cancel')">Cancel</button>
      <button type="button" class="confirm-btn confirm-btn-danger" :disabled="busy" @click="emit('confirm')">
        <span v-if="busy" class="confirm-spinner animate-spin" aria-hidden="true"></span>
        {{ busy ? 'Deleting…' : confirmLabel }}
      </button>
    </div>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useId } from 'vue'
import Icon, { ICONS } from '@/components/Icons'
import BaseDialog from './BaseDialog.vue'

defineProps<{
  open: boolean
  title: string
  confirmLabel: string
  busy?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const titleId = useId()
</script>

<style scoped>
@reference "tailwindcss";

.confirm-dialog {
  width: min(28rem, calc(100vw - 2rem));
}

.confirm-body {
  display: flex;
  gap: 1rem;
}

.confirm-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.75rem;
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.icon-svg {
  width: 1.375rem;
  height: 1.375rem;
}

.confirm-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #f1f5f9;
}

.confirm-message {
  margin-top: 0.375rem;
  color: #94a3b8;
  font-size: 0.875rem;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.confirm-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.confirm-btn:not(:disabled):hover {
  background: rgba(255, 255, 255, 0.12);
}

.confirm-btn-danger {
  color: #fff;
  background: #dc2626;
  border-color: #dc2626;
}

.confirm-btn-danger:not(:disabled):hover {
  background: #b91c1c;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.confirm-spinner {
  width: 0.875rem;
  height: 0.875rem;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
}
</style>
