<template>
  <!-- Native <dialog>: showModal() gives the backdrop, focus trap and Escape for free. -->
  <dialog ref="dialog" @cancel.prevent="emit('dismiss')" @click.self="backdropClose && emit('dismiss')">
    <slot />
  </dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  backdropClose?: boolean
}>()

const emit = defineEmits<{
  dismiss: []
}>()

const dialog = ref<HTMLDialogElement>()

// The top layer stacks in opening order: the toasts' popover (App.vue) re-enters it to stay above this modal.
function raiseToasts() {
  const layer = document.querySelector<HTMLElement>('[data-toasts]')
  if (!layer?.showPopover) return
  layer.hidePopover()
  layer.showPopover()
}

watch(
  () => props.open,
  (open) => {
    if (open && !dialog.value?.open) {
      dialog.value?.showModal?.()
      raiseToasts()
    }
    if (!open && dialog.value?.open) dialog.value.close()
  },
  { flush: 'post' }
)
</script>

<style scoped>
/* Element selectors: a caller's class on this root wins over these defaults. */
dialog {
  margin: auto;
  padding: 1.5rem;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
}

dialog::backdrop {
  background: rgba(2, 6, 23, 0.7);
  backdrop-filter: blur(2px);
}

dialog[open] {
  animation: dialog-in 0.15s ease-out;
}

@keyframes dialog-in {
  from {
    opacity: 0;
    transform: translateY(0.5rem) scale(0.98);
  }
}
</style>

<style>
/* Not scoped: the action buttons of the dialogs built on this one (ConfirmDialog, ImpactDialog). */
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.dialog-btn {
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

.dialog-btn:not(:disabled):hover {
  filter: brightness(1.2);
}

.dialog-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-btn-danger {
  color: #fff;
  background: #dc2626;
  border-color: #dc2626;
}
</style>
