<template>
  <!-- New pass or resume a paused one: on the page, and in the opening dialog when the month has a paused pass. -->
  <DefinePassChoice>
    <fieldset class="space-y-2 text-sm text-foreground" data-test="pass-choice">
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
  </DefinePassChoice>

  <!-- @container: the cards side by side once the page (not the screen) is wide enough. -->
  <div class="@container space-y-6">
    <!-- Page header (shadcn Item): Start on the right, once the state is known. -->
    <Item class="p-0" data-test="page-header">
      <ItemContent>
        <ItemTitle><h2 class="text-2xl font-bold">Start a pass</h2></ItemTitle>
        <ItemDescription class="line-clamp-none">Choose the cycle, then start a new pass or resume a paused one. The forecast page follows.</ItemDescription>
      </ItemContent>
      <ItemActions v-if="state">
        <Button size="lg" :disabled="busy" @click="start">Start</Button>
      </ItemActions>
    </Item>

    <div class="grid grid-cols-[minmax(0,1fr)] items-start gap-6 @4xl:grid-cols-2">
      <div class="space-y-6">
        <!-- The mode first: it decides which passes exist (a pass lives in one mode). -->
        <!-- DRYRUN follows the mode (DRYRUN = TEST MODE): never chosen here. -->
        <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy" @change="changeMode" />

        <Card class="gap-4 py-4" data-test="pass-card">
          <CardHeader class="px-4"><CardTitle>The pass</CardTitle></CardHeader>
          <CardContent class="space-y-6 px-4">
            <div v-if="chosen" class="flex items-center gap-2 text-sm font-medium text-foreground">
              Cycle
              <CyclePicker v-model="month" :disabled="busy" />
            </div>

            <p v-if="!state" class="text-sm text-muted-foreground">Loading the pipeline state…</p>
            <!-- The GEE variables are chosen in Import GEE, on the forecast page (gee-import.md). -->
            <ReusePassChoice v-else />
          </CardContent>
        </Card>
      </div>

      <Card v-if="state" class="gap-4 py-4" data-test="parameters-card">
        <CardHeader class="px-4"><CardTitle>Parameters of this pass</CardTitle></CardHeader>
        <CardContent class="px-4">
          <p v-if="configStore.error" class="mb-2 text-sm text-destructive">{{ configStore.error }}</p>
          <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
            <template v-for="[name, value] in parameters" :key="name">
              <dt class="text-muted-foreground">{{ name }}</dt>
              <dd class="wrap-anywhere text-foreground">{{ value }}</dd>
            </template>
          </dl>
          <p class="mt-2 text-xs text-muted-foreground">
            Fixed for the whole pass when it starts: a later change in Admin Config or of the DHIS2 login applies to the
            next pass only (a launch from a session on another DHIS2 is refused). A resumed pass keeps its own values.
            DHIS2 writes follow the mode: test mode is always a dry run, production always writes.
          </p>
        </CardContent>
      </Card>
    </div>
    <!-- Closing it any way keeps the month shown: it stays editable at the top of the page. -->
    <Dialog :open="askCycle" @update:open="chosen = true">
      <DialogContent data-test="cycle-dialog">
        <form class="grid gap-4" @submit.prevent="chosen = true">
          <DialogHeader>
            <DialogTitle>Choose the mode, then the cycle</DialogTitle>
            <DialogDescription>Test or production first, then the month of the pass. Both stay editable at the top of the page.</DialogDescription>
          </DialogHeader>
          <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy" @change="changeMode" />
          <div class="flex items-center gap-2 text-sm font-medium">
            Cycle
            <CyclePicker v-model="month" />
          </div>
          <ReusePassChoice v-if="paused.length" />
          <DialogFooter>
            <Button type="submit">Continue</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
    <ImpactDialog :pending="pending" :busy="busy" @confirm="confirmNew" @cancel="cancel" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { createReusableTemplate } from '@vueuse/core'
import { useRouter } from 'vue-router'
import ImpactDialog from '@/views/Dashboard/components/ImpactDialog.vue'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import CyclePicker from './CyclePicker.vue'
import { useJournal } from '@/composables/useJournal'
import { usePipeline } from '@/composables/usePipeline'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Item, ItemActions, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useConfigStore } from '@/stores/config'

const router = useRouter()
const [DefinePassChoice, ReusePassChoice] = createReusableTemplate()
const { state, busy, pending, refresh, setCycle, setMode, resume, startPass, confirm, cancel } = usePipeline(() => {}) // no Recent Activity on this page
const { cycles, loadCycles } = useJournal()
const configStore = useConfigStore()

const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`) // 'YYYY-MM', the current month first
const chosen = ref(false) // the opening dialog was closed: the cycle moves to the top of the page
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

// Asked once the state is known, unless a pass is active (the page then leaves for the forecast page).
const askCycle = computed(() => !chosen.value && state.value != null && state.value.pass?.state !== 'active')
// A month with a paused pass: resuming is the default (a new pass needs a confirm, the paused one stays).
watch(paused, list => { choice.value = list[0]?.id ?? 'new' })

const passLabel = computed(() => (choice.value === 'new' ? 'new pass' : `resume ${choice.value}`))

// The paused pass to resume: its configuration, fixed when it started (null for a pass from before 2026-11-20).
const resumed = computed(() => paused.value.find(p => p.id === choice.value) ?? null)
// What the pass imports: chosen in Import GEE (forecast page); a paused pass shows its choice (null: all).
const geeShown = computed(() => {
  if (!resumed.value) return 'chosen in Import GEE (Data Import), all until then'
  return resumed.value.gee_variables?.split(',').join(', ') ?? 'all available variables'
})
const parameters = computed(() => {
  const config = configStore.config
  return [
    ['Cycle', monthName(cycle.value)],
    ['Pass', passLabel.value],
    ['Mode', state.value?.test_mode ? 'test (kept apart from production)' : 'production'],
    ['DHIS2 writes', state.value?.dry_run ? 'Dry run: nothing is written' : 'No dry run: jobs write to DHIS2'],
    ['DHIS2', resumed.value?.dhis_url ?? config?.dhis_url ?? '-'],
    ['PARENT_OU', resumed.value?.parent_ou ?? config?.parent_ou ?? '-'],
    ['GEE_VARIABLES', geeShown.value || '-'],
    ['LOG_LEVEL', resumed.value?.log_level ?? config?.log_level ?? '-'],
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

async function confirmNew(choice?: string): Promise<void> {
  const startingPass = choice === undefined // a choice answers a mode switch, which stays on Home
  if ((await confirm(choice)) && startingPass) await router.push({ name: 'Dashboard' })
}

const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

onMounted(() => Promise.all([refresh(), loadCycles(), configStore.fetchConfig()]))
</script>
