<template>
  <div class="grid gap-6 md:grid-cols-[16rem_1fr]">
    <!-- The cycles that have a history, newest first: one click shows its journal. Above the journal on small screens. -->
    <nav aria-label="Cycles" class="space-y-2">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400">Cycles</h2>
      <!-- One native <details> per year: the newest year and the one of the selected cycle start open. -->
      <details v-for="[year, list] in years" :key="year" :open="year === years[0][0] || year === cycle.slice(0, 4)" class="space-y-2">
        <summary class="cursor-pointer text-sm text-gray-300">{{ year }}</summary>
        <button
          v-for="c in list"
          :key="c.cycle"
          type="button"
          class="mt-2 block w-full rounded-lg border px-3 py-2 text-left text-sm"
          :class="c.cycle === cycle ? 'border-blue-500 bg-gray-800' : 'border-gray-700 bg-gray-900 hover:bg-gray-800'"
          :aria-current="c.cycle === cycle ? 'true' : undefined"
          @click="select(c.cycle)"
        >
          <span class="block font-semibold text-gray-100">{{ monthName(c.cycle) }}</span>
          <span class="block text-xs" :class="c.state === 'closed' ? 'text-green-400' : 'text-gray-400'">
            {{ c.state === 'closed' ? 'complete' : 'open' }}<template v-if="c.target"> · launches go here</template>
          </span>
          <!-- The test checkpoints still in Redis (test mode): their own state, next to production's. -->
          <span v-if="c.test_state" class="block text-xs text-yellow-300">test: {{ c.test_state === 'closed' ? 'complete' : 'open' }}</span>
          <span class="block text-xs text-gray-500">
            {{ c.events }} event{{ c.events === 1 ? '' : 's' }}
            <span v-if="c.test_events" class="ml-1 rounded bg-yellow-900 px-1.5 text-yellow-300">+{{ c.test_events }} test</span>
            <template v-if="c.last_at"> · {{ formatTime(c.last_at) }}</template>
          </span>
        </button>
      </details>
      <p v-if="!cycles.length && !loading" class="text-sm text-gray-500">No cycle yet.</p>
    </nav>

    <div class="min-w-0 space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <h1 class="text-2xl font-bold text-gray-100">{{ cycle ? `Journal · ${monthName(cycle)}` : 'Cycle journal' }}</h1>
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <select v-model="mode" aria-label="Mode" class="rounded-md border border-gray-600 bg-gray-800 px-2 py-1 text-gray-200">
            <option value="">Both modes</option>
            <option value="production">Production</option>
            <option value="test">Test</option>
          </select>
          <select v-model="step" aria-label="Step" class="rounded-md border border-gray-600 bg-gray-800 px-2 py-1 text-gray-200">
            <option value="">All steps</option>
            <option v-for="s in STEPS" :key="s" :value="s">{{ s }}</option>
          </select>
          <button
            class="rounded-md bg-gray-800 px-4 py-1.5 text-gray-300 hover:bg-gray-700"
            :disabled="loading"
            @click="refresh"
          >
            {{ loading ? 'Loading...' : 'Refresh' }}
          </button>
          <!-- etlhub enforces it too (403): the CSV export is for administrators. -->
          <a
            v-if="isAdmin"
            class="rounded-md bg-gray-800 px-4 py-1.5 text-blue-400 hover:bg-gray-700"
            :href="csvUrl(cycle)"
            :class="{ 'pointer-events-none opacity-50': !cycle }"
            download
          >
            Export CSV
          </a>
        </div>
      </div>

      <p class="text-xs text-gray-500">
        Every change of the cycle, oldest first. Refused actions (409) are not events: see Tracking.
        Not seen: <code>DELETE /output/reset</code>, the <code>pridec</code> command line, build_analytics launched from DHIS2.
        Test events stay in Redis only and disappear if Redis is flushed.
      </p>

      <div v-if="error" class="rounded-lg border border-red-900 bg-red-950 p-3 text-sm text-red-300">{{ error }}</div>

      <div class="overflow-x-auto rounded-lg border border-gray-700">
        <table class="min-w-full text-sm">
          <thead class="bg-gray-800 text-left text-gray-200">
            <tr>
              <th class="px-3 py-2">Time</th>
              <th class="px-3 py-2">Step</th>
              <th class="px-3 py-2">Item</th>
              <th class="px-3 py-2">Event</th>
              <th class="px-3 py-2">Actor</th>
              <th class="px-3 py-2">Request</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-700 bg-gray-900 text-gray-300">
            <tr
              v-for="(e, index) in shown"
              :key="index"
              :class="{ 'cursor-pointer hover:bg-gray-800': hasDetail(e) }"
              @click="hasDetail(e) && (selected = e)"
            >
              <td class="whitespace-nowrap px-3 py-2 text-xs text-gray-400">
                {{ formatTime(e.at) }}
                <span v-if="e.mode === 'test'" class="ml-1 rounded bg-yellow-900 px-1.5 py-0.5 text-yellow-300">test</span>
              </td>
              <td class="px-3 py-2 text-xs">{{ e.step ?? '-' }}</td>
              <td class="px-3 py-2 font-mono text-xs break-all">{{ e.item ?? '-' }}</td>
              <td class="px-3 py-2">
                <span class="font-semibold" :class="EVENT_COLORS[e.event] ?? 'text-gray-200'">{{ e.event }}</span>
                <span v-if="e.detail" class="ml-2 text-xs text-gray-500">{{ formatDetail(e.detail) }}</span>
              </td>
              <td class="px-3 py-2 text-xs">{{ e.actor ?? '-' }}</td>
              <td class="whitespace-nowrap px-3 py-2 text-xs">
                <template v-if="e.request">{{ e.request.method }} {{ e.request.status_code }}</template>
                <template v-else>-</template>
              </td>
            </tr>
            <tr v-if="!shown.length && !loading">
              <td colspan="6" class="px-4 py-6 text-center text-gray-500">No event for this cycle.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Same detail as Tracking: the request, then the job logs. -->
      <div
        v-if="selected"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
        @click.self="selected = null"
      >
        <div class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
          <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
            <h2 class="text-base font-semibold text-gray-100">{{ selected.event }} · {{ selected.item ?? selected.cycle }}</h2>
            <button class="rounded-md bg-gray-700 px-3 py-1 text-sm text-gray-300 hover:bg-gray-600" @click="selected = null">
              Close
            </button>
          </div>
          <div class="space-y-4 p-4">
            <RequestDetail v-if="selected.request" :request="selected.request" />
            <JobLogsPanel v-if="selected.job_id && JOB_EVENTS.has(selected.event)" :job-id="selected.job_id" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useJournal } from '@/composables/useJournal'
import type { JournalEvent } from '@/types/pipeline'
import RequestDetail from '@/views/TrackerView/components/RequestDetail.vue'
import JobLogsPanel from '@/views/TrackerView/components/JobLogsPanel.vue'

const STEPS = ['data_import', 'forecast', 'system_update']
// Events of a real job: they have logs. Uploads and decisions have none.
const JOB_EVENTS = new Set(['launched', 'succeeded', 'failed', 'lock_released'])
const EVENT_COLORS: Record<string, string> = {
  succeeded: 'text-green-400',
  failed: 'text-red-400',
  reset: 'text-yellow-400',
  run_abandoned: 'text-yellow-400',
  lock_released: 'text-yellow-400',
  cycle_closed: 'text-green-400',
}

const route = useRoute()
const router = useRouter()
const { cycles, events, loading, error, load, loadCycles, csvUrl } = useJournal()
const isAdmin = computed(() => useAuthStore().user?.is_admin === true)

// ?cycle=YYYYMM (the Dashboard link), else the target cycle once the list is loaded.
const query = route.query.cycle
const cycle = ref(typeof query === 'string' && /^\d{6}$/.test(query) ? query : '')
const mode = ref('')
const step = ref('')
const selected = ref<JournalEvent | null>(null)

// Cycles come newest first: grouping keeps that order, years included.
const years = computed(() => {
  const groups = new Map<string, typeof cycles.value>()
  for (const c of cycles.value) groups.set(c.cycle.slice(0, 4), [...(groups.get(c.cycle.slice(0, 4)) ?? []), c])
  return [...groups]
})

const shown = computed(() =>
  events.value.filter(e => (!mode.value || e.mode === mode.value) && (!step.value || e.step === step.value))
)

const hasDetail = (e: JournalEvent) => e.request != null || (e.job_id != null && JOB_EVENTS.has(e.event))
const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
const formatDetail = (detail: Record<string, unknown>) =>
  Object.entries(detail).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`).join(' · ')

function select(c: string) {
  cycle.value = c
  router.replace({ query: { ...route.query, cycle: c } }) // shareable, kept on reload; Back leaves the page
  load(c)
}

async function refresh() {
  await loadCycles()
  cycle.value ||= cycles.value.find(c => c.target)?.cycle ?? cycles.value[0]?.cycle ?? ''
  if (cycle.value) await load(cycle.value)
}

onMounted(refresh)
</script>
