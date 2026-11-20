<template>
  <!-- Large dialog: header (title, badge, actions; shadcn's close cross on the right), scrolling body, optional footer.
       The caller's class / data-test go on the content box (the Dialog root renders no element). -->
  <Dialog :open="open" @update:open="!$event && emit('close')">
    <DialogContent v-bind="$attrs" class="flex h-[90vh] w-[min(96vw,1600px)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-w-none" :aria-describedby="undefined">
      <header class="flex flex-wrap items-center justify-between gap-4 border-b bg-card py-4 pr-14 pl-6">
        <div class="flex min-w-0 flex-wrap items-center gap-3">
          <Eye class="size-5 text-primary" />
          <DialogTitle class="font-mono font-bold">{{ title }}</DialogTitle>
          <span v-if="source" class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="BADGES[source].class">
            {{ BADGES[source].text }}
          </span>
        </div>
        <div class="flex items-center gap-3">
          <slot name="actions" />
        </div>
      </header>

      <div class="min-h-0 flex-1 overflow-auto px-6 py-5">
        <div v-if="loading" class="flex h-full items-center justify-center gap-3 text-muted-foreground" role="status">
          <LoaderCircle class="size-5 animate-spin text-primary" aria-hidden="true" />
          {{ loadingLabel ?? 'Loading preview…' }}
        </div>
        <div v-else-if="error" class="flex h-full items-center justify-center text-destructive" role="alert">{{ error }}</div>
        <slot v-else />
      </div>
      <div v-if="$slots.footer" class="flex justify-end gap-3 border-t bg-card px-6 py-4" data-test="preview-footer"><slot name="footer" /></div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { Eye, LoaderCircle } from '@lucide/vue'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'

defineOptions({ inheritAttrs: false })

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

const BADGES = {
  server: { text: 'On server', class: 'bg-success/15 text-success' },
  local: { text: 'Selected file — not uploaded', class: 'bg-warning/15 text-warning' },
  default: { text: 'Default file', class: 'bg-primary/15 text-primary' }
}
</script>
