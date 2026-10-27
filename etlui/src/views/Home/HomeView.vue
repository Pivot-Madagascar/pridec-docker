<template>
  <Card class="mx-auto max-w-3xl gap-0 space-y-6 p-8">
    <div>
      <h1 class="text-2xl font-bold text-gray-100">Start a pass</h1>
      <p class="text-sm text-gray-400">Choose the cycle, then start a new pass or resume a paused one. The forecast page follows.</p>
    </div>

    <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy || state?.lock != null" @change="changeMode" />

    <p v-if="!state" class="text-sm text-gray-400">Loading the pipeline state…</p>
    <form v-else class="space-y-6" @submit.prevent="start">
      <Label>
        Cycle
        <!-- A pass is active: the server refuses another month until it is paused or abandoned. -->
        <Input
          v-model="month"
          type="month"
          required
          :max="thisMonth"
          :disabled="busy || active != null"
          :title="active ? 'Pause or abandon the active pass first (on the forecast page)' : 'Month of the pass'"
          class="w-auto"
        />
      </Label>

      <fieldset v-if="month" class="space-y-2 text-sm text-gray-200">
        <legend class="mb-2 font-semibold">Pass</legend>
        <p v-if="active">
          Pass <span class="font-mono">{{ active.id }}</span> is active, started {{ formatTime(active.started_at) }} by
          {{ active.started_by ?? '-' }}: Start continues it.
        </p>
        <template v-else>
          <label class="block">
            <input v-model="choice" type="radio" value="new" :disabled="paused.length > 0" />
            New pass
            <span class="text-xs text-gray-400">
              <template v-if="paused.length">· resume or abandon (Journal) the paused pass first</template>
              <template v-else-if="complete">· the month is complete: the first launch asks to confirm a new pass</template>
              <template v-else>· starts at the first launch</template>
            </span>
          </label>
          <label v-for="p in paused" :key="p.id" class="block">
            <input v-model="choice" type="radio" :value="p.id" />
            Resume paused pass <span class="font-mono">{{ p.id }}</span>
            <span class="text-xs text-gray-400">· started {{ formatTime(p.started_at) }} by {{ p.started_by ?? '-' }}</span>
          </label>
        </template>
      </fieldset>

      <div v-if="month">
        <h2 class="mb-2 text-sm font-semibold text-gray-200">Parameters of this pass</h2>
        <p v-if="configStore.error" class="mb-2 text-sm text-red-300">{{ configStore.error }}</p>
        <dl class="grid grid-cols-[12rem_1fr] gap-x-4 gap-y-1 text-sm">
          <template v-for="[name, value] in parameters" :key="name">
            <dt class="text-gray-400">{{ name }}</dt>
            <dd class="break-all text-gray-100">{{ value }}</dd>
          </template>
        </dl>
        <p class="mt-2 text-xs text-gray-500">
          Values now. PARENT_OU, GEE_VARIABLES and LOG_LEVEL are edited in Admin Config and apply to the launches after the change;
          DRYRUN comes from the root .env.
        </p>
      </div>

      <div class="flex justify-end">
        <Button type="submit" size="lg" :disabled="busy || !month">Start</Button>
      </div>
    </form>
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import { useJournal } from '@/composables/useJournal'
import { usePipeline } from '@/composables/usePipeline'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfigStore } from '@/stores/config'

const router = useRouter()
const { state, busy, refresh, setCycle, setMode, resume } = usePipeline(() => {}) // no Recent Activity on this page
const { cycles, loadCycles } = useJournal()
const configStore = useConfigStore()

const now = new Date()
const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}` // the server refuses a future month
const month = ref('') // 'YYYY-MM' of <input type="month">
const choice = ref('new') // 'new' or the id of a paused pass

const active = computed(() => (state.value?.pass?.state === 'active' ? state.value.pass : null))
const cycle = computed(() => month.value.replace('-', ''))
// A pass lives in one mode: only the passes of the current mode can be resumed. Newest first (GET /pipeline/cycles).
const passes = computed(() => {
  const mode = state.value?.test_mode ? 'test' : 'production'
  return cycles.value.find(c => c.cycle === cycle.value)?.passes.filter(p => p.mode === mode) ?? []
})
const paused = computed(() => passes.value.filter(p => p.state === 'paused'))
const complete = computed(() => passes.value[0]?.state === 'complete')

// The target month of the server, or the active pass's month, until the user picks one.
watch(() => active.value?.cycle ?? state.value?.cycle, c => {
  if (c && (!month.value || active.value)) month.value = `${c.slice(0, 4)}-${c.slice(4)}`
})
// A month with a paused pass refuses a new one: resuming is the default.
watch(paused, list => { choice.value = list[0]?.id ?? 'new' })

const passLabel = computed(() => {
  if (active.value) return `continue ${active.value.id}`
  return choice.value === 'new' ? 'new pass' : `resume ${choice.value}`
})
const parameters = computed(() => {
  const config = configStore.config
  return [
    ['Cycle', monthName(cycle.value)],
    ['Pass', passLabel.value],
    ['Mode', state.value?.test_mode ? 'test (kept apart from production)' : 'production'],
    ['DHIS2 writes', state.value?.dry_run ? 'DRYRUN on: nothing is written' : 'DRYRUN off: jobs write to DHIS2'],
    ['DHIS2', config?.dhis_url ?? '-'],
    ['PARENT_OU', config?.parent_ou ?? '-'],
    ['GEE_VARIABLES', config?.gee_variables || 'all available variables'],
    ['LOG_LEVEL', config?.log_level ?? '-'],
    ['OU_LEVEL, DISEASE_CODE', 'set by each forecast run, opened on the forecast page']
  ]
})

const changeMode = async (testMode: boolean) => {
  await setMode(testMode)
  await loadCycles() // leaving test mode pauses the active test pass
}

// Each call shows its own toast; a refusal keeps the user here.
async function start(): Promise<void> {
  const ok = active.value
    ? true
    : choice.value !== 'new'
      ? await resume(choice.value)
      : cycle.value === state.value?.cycle || (await setCycle(cycle.value))
  if (ok) await router.push({ name: 'Dashboard' })
}

const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

onMounted(() => Promise.all([refresh(), loadCycles(), configStore.fetchConfig()]))
</script>
