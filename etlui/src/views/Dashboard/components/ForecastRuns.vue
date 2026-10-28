<template>
  <div class="forecast-runs" data-test="forecast-runs">
    <p class="todo" data-test="todo" role="status"><strong>To do now:</strong> {{ todo }}</p>

    <!-- One tab per disease. Hidden tabs stay mounted (force-mount, hidden by CSS: reka then never sets `hidden`): files picked in a run's steps are kept, and the
         breadcrumb's "go to the current item" reaches the open run's card. -->
    <Tabs v-model="tab">
      <TabsList data-test="disease-tabs" aria-label="Diseases">
        <TabsTrigger v-for="disease in DISEASES" :key="disease" :value="disease">{{ DISEASE_NAMES[disease] }}</TabsTrigger>
      </TabsList>
      <TabsContent v-for="disease in DISEASES" :key="disease" :value="disease" force-mount class="mt-4 data-[state=inactive]:hidden">
        <DiseaseCard :id="`forecast-${disease}`" :disease="disease" />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import DiseaseCard from '@/views/Dashboard/components/DiseaseCard.vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DISEASE_NAMES, ITEM_NAMES, coupleName, jobOf, labelOf, nextItem, step } from '@/config/pipeline'
import { DISEASES, type Disease } from '@/types/pipeline'
import { RUNS, type RunsEmit, type RunsProps } from './runs'

const props = defineProps<RunsProps>()
const emit = defineEmits<RunsEmit>()
provide(RUNS, { props, emit })

// The open run's disease tab: shown at first, when a run opens, and on each "go to the current item" (a new focus).
const tab = ref<Disease>(DISEASES[0])
const runDisease = computed(() => props.state?.run?.couple.split('/')[1] as Disease | undefined)
watch([runDisease, () => props.focus], ([disease]) => { if (disease) tab.value = disease }, { immediate: true })

const forecastStep = computed(() => step(props.state, 'forecast'))

// The next human action, read from the open run and what etlhub says can start.
const todo = computed(() => {
  const state = props.state
  if (!state) return 'loading…'
  if (state.lock) return `wait, “${ITEM_NAMES[state.lock.task] ?? labelOf(state.lock.task)}” is running.`
  if (!forecastStep.value?.accessible) return 'finish step 1 (data import) first.'
  const run = state.run
  if (!run) {
    const left = forecastStep.value.items.some(i => i.item.endsWith(':post_forecast') && i.status !== 'success')
    return left ? 'open a forecast run below.' : "all of this month's forecasts are published."
  }
  const name = coupleName(run.couple)
  const next = nextItem(state, 'forecast')
  if (!next) return `nothing to launch for ${name}.`
  if (next.item.startsWith('config/')) return `provide the parameters of ${name} (click its card).`
  if (next.item.startsWith('external_data/')) return `provide the external data of ${name} (click its card).`
  const job = jobOf(next.item)
  return job === 'approve' ? `approve ${name}.` : `launch “${ITEM_NAMES[job] ?? job}” for ${name}.`
})
</script>

<style>
/* Step ② only: not scoped, so DiseaseCard and LevelColumn share it. */
.forecast-runs {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  color: var(--foreground);
}

.forecast-runs .hint {
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.forecast-runs .todo {
  padding: 1rem 1.25rem;
  border-radius: 0.75rem;
  background: color-mix(in oklab, var(--warning) 10%, transparent);
  border: 1px solid color-mix(in oklab, var(--warning) 45%, transparent);
  color: var(--warning);
}

.forecast-runs a:focus-visible,
.forecast-runs summary:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.forecast-runs .disease-card {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2.5rem;
  border-radius: 1rem;
  background: var(--muted);
  border: 1px solid var(--border);
}

.forecast-runs .card-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
}

.forecast-runs .card-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--foreground);
}

.forecast-runs .card-progress {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--foreground);
}

.forecast-runs .progress-dots {
  display: flex;
  gap: 0.375rem;
}

.forecast-runs .progress-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 9999px;
  border: 2px solid var(--border);
}

.forecast-runs .progress-dot.is-done {
  background: var(--success);
  border-color: var(--success);
}

.forecast-runs code {
  font-size: 0.75rem;
  color: var(--muted-foreground);
}

/* Every card of a carousel as tall as the tallest. */
.forecast-runs [data-slot="carousel-item"] > .level-column {
  height: 100%;
}

.forecast-runs .level-column {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  border-radius: 0.75rem;
  background: var(--card);
  border: 1px solid var(--border);
}

/* The open run: highlighted, and the whole card is the button to its steps. */
.forecast-runs .level-column.is-open {
  border-color: var(--primary);
  background: color-mix(in oklab, var(--primary) 12%, transparent);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--primary) 35%, transparent);
}

.forecast-runs .card-steps {
  position: absolute;
  inset: 0;
  border: 0;
  border-radius: inherit;
  background: transparent;
  cursor: pointer;
}

.forecast-runs .card-steps:hover {
  background: color-mix(in oklab, var(--primary) 10%, transparent);
}

.forecast-runs .card-steps:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.forecast-runs .card-steps-hint {
  color: var(--primary);
  font-size: 0.8125rem;
}


.forecast-runs .level-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--foreground);
}

.forecast-runs .level-code {
  font-size: 0.75rem;
  color: var(--muted-foreground);
}

.forecast-runs .level-status {
  font-weight: 600;
}

.forecast-runs .status-published,
.forecast-runs .text-success {
  color: var(--success);
}

.forecast-runs .status-waiting,
.forecast-runs .text-todo {
  color: var(--warning);
}

.forecast-runs .status-open {
  color: var(--primary);
}

.forecast-runs .status-idle {
  color: var(--muted-foreground);
  font-size: 0.875rem;
}

.forecast-runs .level-progress {
  color: var(--muted-foreground);
  font-size: 0.875rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Title (shadcn's close cross sits top right). */
.forecast-runs .steps-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

/* 4 columns, each headed by its step: input files | the 3 fetches and the data check | forecast (+ CSB alerts) and
   approval | publication. 2 per row, then 1, on narrower screens. */
.forecast-runs .steps-columns {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.forecast-runs .step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.forecast-runs .step-mark {
  display: grid;
  place-items: center;
  flex: none;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  border: 2px solid var(--border);
  background: var(--card);
  color: var(--muted-foreground);
  font-size: 0.875rem;
  font-weight: 700;
  transition: background-color 0.3s, border-color 0.3s, box-shadow 0.3s;
}

.forecast-runs .step-title {
  font-weight: 600;
  color: var(--foreground);
}

/* The line to the next step, across the gap. */
.forecast-runs .steps-column:not(:last-child) .step::after {
  content: '';
  flex: 1;
  height: 2px;
  margin-right: -1rem;
  background: var(--border);
}

/* A done column: its step glows green. */
.forecast-runs .step.is-done .step-mark {
  border-color: var(--success);
  background: var(--success);
  color: var(--primary-foreground);
  box-shadow: 0 0 0 4px color-mix(in oklab, var(--success) 30%, transparent), 0 0 12px var(--success);
}

.forecast-runs .steps-column:not(:last-child) .step.is-done::after {
  background: var(--success);
}

@media (max-width: 1280px) {
  .forecast-runs .steps-columns {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .forecast-runs .steps-column:not(:last-child) .step::after {
    display: none;
  }
}

@media (max-width: 640px) {
  .forecast-runs .steps-columns {
    grid-template-columns: minmax(0, 1fr);
  }
}

.forecast-runs .steps-dialog .item {
  align-content: start;
  padding: 0.875rem;
  border-radius: 0.75rem;
  background: var(--card);
  border: 1px solid var(--border);
}

.forecast-runs .data-check {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

/* The text on the left, the data check button on the right. */
.forecast-runs .data-check .item-text {
  margin-right: auto;
}

.forecast-runs .item-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
}

.forecast-runs .item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.75rem;
}

/* An input row: the dropzone takes the full width under its label. */
.forecast-runs .item-file {
  grid-column: 1 / -1;
}

.forecast-runs .item-dot {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 9999px;
  background: var(--muted-foreground);
}

.forecast-runs .item-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.forecast-runs .item-label {
  font-size: 0.9375rem;
  color: var(--foreground);
}

.forecast-runs .item-tech {
  font-size: 0.6875rem;
}

.forecast-runs .item-state {
  font-size: 0.75rem;
  color: var(--muted-foreground);
}

.forecast-runs .item-pending .item-label {
  color: var(--muted-foreground);
}

.forecast-runs .item-success .item-dot {
  background: var(--success);
}

.forecast-runs .item-waiting .item-dot {
  background: var(--warning);
  box-shadow: 0 0 0 4px color-mix(in oklab, var(--warning) 30%, transparent);
}

.forecast-runs .item-waiting .item-state {
  color: var(--warning);
}

.forecast-runs .item-running .item-dot {
  background: transparent;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  animation: forecast-spin 0.8s linear infinite;
}

.forecast-runs .item-running .item-state {
  color: var(--primary);
}

.forecast-runs .item-error .item-dot {
  background: var(--destructive);
}

.forecast-runs .item-error .item-state {
  color: var(--destructive);
}

.forecast-runs .level-action {
  position: relative; /* above .card-steps */
  margin-top: auto;
}

@keyframes forecast-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .forecast-runs .item-running .item-dot {
    animation: none;
  }
}

@media (max-width: 820px) {
  .forecast-runs .disease-card {
    padding: 1.5rem;
  }
}
</style>
