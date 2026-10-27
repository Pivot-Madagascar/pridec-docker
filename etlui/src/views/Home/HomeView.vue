<template>
  <Card class="mx-auto max-w-3xl gap-0 space-y-6 p-8">
    <div>
      <h1 class="text-2xl font-bold text-foreground">Start a pass</h1>
      <p class="text-sm text-muted-foreground">Choose the cycle, then start a new pass or resume a paused one. The forecast page follows.</p>
    </div>

    <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy || state?.lock != null" @change="changeMode" />

    <p v-if="!state" class="text-sm text-muted-foreground">Loading the pipeline state…</p>
    <form v-else class="space-y-6" @submit.prevent="start">
      <Label>
        Cycle
        <Input v-model="month" type="month" required :max="thisMonth" :disabled="busy" title="Month of the pass" class="w-auto" />
      </Label>

      <fieldset v-if="month" class="space-y-2 text-sm text-foreground">
        <legend class="mb-2 font-semibold">Pass</legend>
        <RadioGroup v-model="choice">
          <Label class="font-normal">
            <RadioGroupItem value="new" />
            New pass
            <span class="text-xs text-muted-foreground">
              <template v-if="paused.length">· the paused pass stays paused: Start asks to confirm a new pass</template>
              <template v-else-if="complete">· the month is complete: Start asks to confirm a new pass</template>
              <template v-else>· starts now, from Data Import</template>
            </span>
          </Label>
          <Label v-for="p in paused" :key="p.id" class="font-normal">
            <RadioGroupItem :value="p.id" />
            Resume paused pass <span class="font-mono">{{ p.id }}</span>
            <span class="text-xs text-muted-foreground">· started {{ formatTime(p.started_at) }} by {{ p.started_by ?? '-' }}</span>
          </Label>
        </RadioGroup>
      </fieldset>

      <div v-if="month">
        <h2 class="mb-2 text-sm font-semibold text-foreground">Parameters of this pass</h2>
        <p v-if="configStore.error" class="mb-2 text-sm text-destructive">{{ configStore.error }}</p>
        <dl class="grid grid-cols-[12rem_1fr] gap-x-4 gap-y-1 text-sm">
          <template v-for="[name, value] in parameters" :key="name">
            <dt class="text-muted-foreground">{{ name }}</dt>
            <dd class="break-all text-foreground">{{ value }}</dd>
          </template>
        </dl>
        <p class="mt-2 text-xs text-muted-foreground">
          Values now. PARENT_OU, GEE_VARIABLES and LOG_LEVEL are edited in Admin Config and apply to the launches after the change;
          DRYRUN comes from the root .env.
        </p>
      </div>

      <div class="flex justify-end">
        <Button type="submit" size="lg" :disabled="busy || !month">Start</Button>
      </div>
    </form>
    <ImpactDialog :pending="pending" :busy="busy" @confirm="confirmNew" @cancel="cancel" />
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ImpactDialog from '@/views/Dashboard/components/ImpactDialog.vue'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import { useJournal } from '@/composables/useJournal'
import { usePipeline } from '@/composables/usePipeline'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useConfigStore } from '@/stores/config'

const router = useRouter()
const { state, busy, pending, refresh, setCycle, setMode, resume, startPass, confirm, cancel } = usePipeline(() => {}) // no Recent Activity on this page
const { cycles, loadCycles } = useJournal()
const configStore = useConfigStore()

const now = new Date()
const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}` // the server refuses a future month
const month = ref('') // 'YYYY-MM' of <input type="month">
const choice = ref('new') // 'new' or the id of a paused pass

// A pass is active: Home has nothing to start, the forecast page takes over (replace: Back does not loop here).
watch(() => state.value?.pass?.state, s => { if (s === 'active') void router.replace({ name: 'Dashboard' }) })
const cycle = computed(() => month.value.replace('-', ''))
// A pass lives in one mode: only the passes of the current mode can be resumed. Newest first (GET /pipeline/cycles).
const passes = computed(() => {
  const mode = state.value?.test_mode ? 'test' : 'production'
  return cycles.value.find(c => c.cycle === cycle.value)?.passes.filter(p => p.mode === mode) ?? []
})
const paused = computed(() => passes.value.filter(p => p.state === 'paused'))
const complete = computed(() => passes.value[0]?.state === 'complete')

// The target month of the server, until the user picks one.
watch(() => state.value?.cycle, c => {
  if (c && !month.value) month.value = `${c.slice(0, 4)}-${c.slice(4)}`
})
// A month with a paused pass: resuming is the default (a new pass needs a confirm, the paused one stays).
watch(paused, list => { choice.value = list[0]?.id ?? 'new' })

const passLabel = computed(() => (choice.value === 'new' ? 'new pass' : `resume ${choice.value}`))
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

// Each call shows its own toast; a refusal keeps the user here. A new pass is started now, so the forecast page
// shows it (not the month's last pass); after a complete or paused pass, ImpactDialog asks to confirm first.
async function start(): Promise<void> {
  const ok =
    choice.value !== 'new'
      ? await resume(choice.value)
      : (cycle.value === state.value?.cycle || (await setCycle(cycle.value))) && (await startPass())
  if (ok) await router.push({ name: 'Dashboard' })
}

async function confirmNew(): Promise<void> {
  if (await confirm()) await router.push({ name: 'Dashboard' })
}

const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

onMounted(() => Promise.all([refresh(), loadCycles(), configStore.fetchConfig()]))
</script>
