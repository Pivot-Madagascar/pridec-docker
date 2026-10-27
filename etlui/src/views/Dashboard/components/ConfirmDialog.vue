<template>
  <!-- An alert dialog: no click outside, Escape = Cancel, nothing closes while busy. -->
  <AlertDialog :open="open" @update:open="!$event && !busy && emit('cancel')">
    <AlertDialogContent class="sm:max-w-md">
      <div class="flex gap-4">
        <div class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-destructive/15 text-destructive">
          <Trash2 class="size-5" />
        </div>
        <div>
          <AlertDialogTitle>{{ title }}</AlertDialogTitle>
          <AlertDialogDescription class="mt-1.5 leading-normal"><slot /></AlertDialogDescription>
        </div>
      </div>
      <AlertDialogFooter>
        <Button variant="outline" :disabled="busy" @click="emit('cancel')">Cancel</Button>
        <Button variant="destructive" data-test="confirm-btn" :disabled="busy" @click="emit('confirm')">
          <LoaderCircle v-if="busy" class="animate-spin" aria-hidden="true" />
          {{ busy ? 'Deleting…' : confirmLabel }}
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

<script setup lang="ts">
import { LoaderCircle, Trash2 } from '@lucide/vue'
import { AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'

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
</script>
