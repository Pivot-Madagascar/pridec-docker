<template>
  <!-- Modal of rule R5: built only from the `impact` etlhub sends with a 409 confirmation_required. -->
  <BaseDialog :open="!!pending" class="impact-dialog" :aria-labelledby="titleId" @dismiss="!busy && emit('cancel')">
    <div v-if="pending" class="impact-body">
      <h3 :id="titleId" class="impact-title">{{ pending.label }}: confirmation required</h3>
      <p class="impact-message">{{ pending.message }}</p>

      <dl class="impact-list">
        <template v-for="entry in entries" :key="entry.key">
          <dt>{{ entry.label }}</dt>
          <dd>{{ entry.value }}</dd>
        </template>
      </dl>

      <ul v-if="pending.impact.step" class="impact-notes">
        <li>The step of this item becomes invalid while it runs again; the next steps are blocked until it is valid.</li>
        <li>Results already produced in the next steps are kept, but they were computed with the previous data.</li>
        <li>If the relaunch fails, the cycle stays at this step until all its items are in success.</li>
      </ul>

      <label class="impact-approve">
        <input v-model="approved" type="checkbox" />
        I have read the impact and I approve this update
      </label>
    </div>
    <div class="dialog-actions">
      <button type="button" class="dialog-btn" :disabled="busy" autofocus @click="emit('cancel')">Cancel</button>
      <button type="button" class="dialog-btn dialog-btn-primary" :disabled="busy || !approved" @click="emit('confirm')">
        Confirm
      </button>
    </div>
  </BaseDialog>
</template>

<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import type { PendingConfirmation } from '@/composables/usePipeline'
import BaseDialog from './BaseDialog.vue'

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
  mode: 'Mode',
  open_run: 'Open run discarded',
  items_in_success: 'Test successes discarded'
}

const titleId = useId()
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

<style scoped>
@reference "tailwindcss";

.impact-dialog {
  width: min(34rem, calc(100vw - 2rem));
}

.impact-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #fbbf24;
}

.impact-message {
  margin-top: 0.5rem;
  color: #cbd5e1;
  font-size: 0.875rem;
}

.impact-list {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.375rem 1rem;
  margin-top: 1rem;
  font-size: 0.8125rem;
}

.impact-list dt {
  color: #94a3b8;
}

.impact-list dd {
  color: #f1f5f9;
  word-break: break-word;
}

.impact-notes {
  margin-top: 1rem;
  padding-left: 1.25rem;
  list-style: disc;
  color: #94a3b8;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.impact-approve {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  margin-top: 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #f1f5f9;
}

.dialog-btn-primary {
  color: #fff;
  background: #d97706;
  border-color: #d97706;
}
</style>
