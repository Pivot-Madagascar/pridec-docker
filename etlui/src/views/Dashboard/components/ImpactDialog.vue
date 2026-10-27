<template>
  <!-- Modal of rule R5: built only from the `impact` etlhub sends with a 409 confirmation_required. -->
  <AlertDialog :open="!!pending" @update:open="!$event && !busy && emit('cancel')">
    <AlertDialogContent class="sm:max-w-xl" data-test="impact-dialog">
      <div v-if="pending" class="text-sm">
        <AlertDialogTitle class="text-warning">{{ pending.label }}: confirmation required</AlertDialogTitle>
        <AlertDialogDescription class="mt-2">{{ pending.message }}</AlertDialogDescription>

        <dl class="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-[0.8125rem]">
          <template v-for="entry in entries" :key="entry.key">
            <dt class="text-muted-foreground">{{ entry.label }}</dt>
            <dd class="break-words">{{ entry.value }}</dd>
          </template>
        </dl>

        <ul v-if="pending.impact.step" class="mt-4 list-disc pl-5 text-[0.8125rem] leading-normal text-muted-foreground">
          <li>The step of this item becomes invalid while it runs again; the next steps are blocked until it is valid.</li>
          <li>Results already produced in the next steps are kept, but they were computed with the previous data.</li>
          <li>If the relaunch fails, the cycle stays at this step until all its items are in success.</li>
        </ul>

        <Label class="mt-4 font-semibold">
          <Checkbox v-model="approved" />
          I have read the impact and I approve this update
        </Label>
      </div>
      <AlertDialogFooter>
        <Button variant="outline" :disabled="busy" @click="emit('cancel')">Cancel</Button>
        <Button :disabled="busy || !approved" @click="emit('confirm')">Confirm</Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PendingConfirmation } from '@/composables/usePipeline'
import { AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

const props = defineProps<{
  pending: PendingConfirmation | null
  busy?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const LABELS: Record<string, string> = {
  item: 'Item',
  step: 'Step',
  current_step: 'Cycle currently at step',
  reset_items: 'Back to pending',
  blocked_steps: 'Blocked until revalidated',
  kept_items: 'Successes kept in the next steps',
  stale_runs: 'Runs already computed with the previous file (kept)',
  cycle: 'Cycle',
  complete_pass: 'Complete pass (kept)',
  paused_pass: 'Paused pass (stays paused, resume it from the Journal)',
  mode: 'Mode',
  open_run: 'Open run discarded',
  items_in_success: 'Test successes discarded'
}

const approved = ref(false)

const format = (value: unknown): string => {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'none'
  if (value && typeof value === 'object') {
    const pairs = Object.entries(value).map(([k, v]) => `${k}: ${v}`)
    return pairs.length ? pairs.join(', ') : 'none'
  }
  return value == null ? 'none' : String(value)
}

const entries = computed(() =>
  Object.entries(props.pending?.impact ?? {}).map(([key, value]) => ({ key, label: LABELS[key] ?? key, value: format(value) }))
)

watch(
  () => props.pending,
  () => {
    approved.value = false // every confirmation is approved on its own
  }
)
</script>
