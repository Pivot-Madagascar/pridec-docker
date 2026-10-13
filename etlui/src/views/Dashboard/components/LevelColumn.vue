<template>
  <!-- One run (level x disease): its status and a progress bar; every item and its launch button are in the "Steps" dialog. -->
  <section class="level-column" :class="{ 'is-open': isOpen }" :aria-labelledby="titleId">
    <h5 :id="titleId" class="level-title">{{ LEVEL_NAMES[source] }} <span class="level-code">{{ source }}</span></h5>
    <p class="level-status" :class="`status-${status.key}`">{{ status.text }}</p>
    <progress class="level-bar" :value="done" :max="items.length"></progress>
    <p class="level-progress">
      {{ done }} of {{ items.length }} steps
      <button type="button" class="btn btn-small" @click="showSteps = true">Steps</button>
    </p>

    <BaseDialog :open="showSteps" backdrop-close class="steps-dialog" :aria-label="`${LEVEL_NAMES[source]} · ${disease}`" @dismiss="showSteps = false">
      <h5 class="level-title">{{ LEVEL_NAMES[source] }} <span class="level-code">{{ source }}</span> · {{ disease }}</h5>
      <ol class="item-list">
        <li v-for="row in rows" :key="row.item" class="item" :class="`item-${row.look}`">
          <span class="item-dot" aria-hidden="true"></span>
          <span class="item-text">
            <span class="item-label">{{ row.label }}</span>
            <code class="item-tech">{{ row.job }}</code>
            <span class="item-state">{{ LOOK_TEXT[row.look] }}</span>
          </span>
          <button
            v-if="row.launch"
            type="button"
            class="btn btn-small"
            :disabled="blocked"
            :aria-label="`${row.launch} : ${row.label}`"
            @click="emit('launch', row.item)"
          >
            {{ row.launch }}
          </button>
        </li>
      </ol>
      <button type="button" class="btn" @click="showSteps = false">Close</button>
    </BaseDialog>

    <div class="level-action">
      <button v-if="status.key === 'published'" type="button" class="btn" @click="emit('report')">View report</button>
      <button v-else-if="status.key === 'waiting'" type="button" class="btn btn-primary" :disabled="blocked" @click="emit('validate')">
        Read and approve
      </button>
      <template v-else-if="!isOpen">
        <p v-if="state?.run" class="hint">Available once the open run is done</p>
        <button v-else type="button" class="btn btn-primary" :disabled="blocked || !accessible" @click="emit('open')">Open</button>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import BaseDialog from './BaseDialog.vue'
import { ITEM_NAMES, LEVEL_NAMES, jobOf, step } from '@/config/pipeline'
import type { Checkpoints, Disease, PipelineItem, Source } from '@/types/pipeline'

const props = defineProps<{
  source: Source
  disease: Disease
  state: Checkpoints | null
  busy: boolean
}>()

const emit = defineEmits<{
  open: []
  launch: [item: string]
  validate: []
  report: []
}>()

type Look = 'success' | 'waiting' | 'running' | 'error' | 'pending'
// Never the colour alone: every state also has its text.
const LOOK_TEXT: Record<Look, string> = {
  success: '✓ Done',
  waiting: '⏳ Waiting for your decision',
  running: '⟳ Running…',
  error: '✗ Failed: relaunch this step',
  pending: 'To do'
}

const titleId = useId()
const showSteps = ref(false)
const couple = computed(() => `${props.source}/${props.disease}`)
const items = computed<PipelineItem[]>(() =>
  (step(props.state, 'forecast')?.items ?? []).filter(i => i.item.startsWith(`${couple.value}:`))
)
const accessible = computed(() => step(props.state, 'forecast')?.accessible ?? false)
const isOpen = computed(() => props.state?.run?.couple === couple.value)
const blocked = computed(() => props.busy || props.state?.lock != null)
const done = computed(() => items.value.filter(i => i.status === 'success').length)
const byJob = (job: string) => items.value.find(i => jobOf(i.item) === job)
const awaiting = (i: PipelineItem) => isOpen.value && jobOf(i.item) === 'approve' && i.status === 'pending' && i.launchable

const status = computed(() => {
  if (byJob('post_forecast')?.status === 'success') return { key: 'published', text: '✓ Published' }
  const approve = byJob('approve')
  if (approve && awaiting(approve)) return { key: 'waiting', text: '⏳ To approve' }
  if (isOpen.value) return { key: 'open', text: '● In progress' }
  return { key: 'idle', text: 'Not started yet' }
})

// The open run's jobs get a button when etlhub says they can start (approve goes through "Read and approve").
const rows = computed(() =>
  items.value.map(i => {
    const job = jobOf(i.item)
    const look: Look = awaiting(i) ? 'waiting' : i.status
    const launchable = isOpen.value && job !== 'approve' && i.launchable && i.status !== 'running'
    return {
      item: i.item, job, look,
      label: ITEM_NAMES[job] ?? job,
      launch: launchable ? (i.status === 'pending' ? 'Launch' : 'Relaunch') : null
    }
  })
)
</script>
