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
    <div class="dialog-actions">
      <Button variant="outline" :disabled="busy" autofocus @click="emit('cancel')">Cancel</Button>
      <Button variant="destructive" data-test="confirm-btn" :disabled="busy" @click="emit('confirm')">
        <LoaderCircle v-if="busy" class="animate-spin" aria-hidden="true" />
        {{ busy ? 'Deleting…' : confirmLabel }}
      </Button>
    </div>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useId } from 'vue'
import { LoaderCircle } from '@lucide/vue'
import Icon, { ICONS } from '@/components/Icons'
import { Button } from '@/components/ui/button'
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

</style>
