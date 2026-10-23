<template>
  <div class="grid gap-6 md:grid-cols-[16rem_1fr]">
    <!-- The months and their passes, newest first: one click shows a pass's journal. Above the journal on small screens. -->
    <nav aria-label="Cycles" class="space-y-2">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400">Cycles</h2>
      <!-- One native <details> per year: the newest year and the one of the selected pass start open. -->
      <details v-for="[year, list] in years" :key="year" :open="year === years[0][0] || year === current?.cycle.slice(0, 4)" class="space-y-2">
        <summary class="cursor-pointer text-sm text-gray-300">{{ year }}</summary>
        <section v-for="c in list" :key="c.cycle" class="mt-2">
          <h3 class="text-sm font-semibold text-gray-100">
            {{ monthName(c.cycle) }}<span v-if="c.target" class="ml-1 text-xs font-normal text-gray-400">· launches go here</span>
          </h3>
          <button
            v-for="p in c.passes"
            :key="p.id"
            type="button"
            class="mt-1 block w-full rounded-lg border px-3 py-2 text-left text-sm"
            :class="p.id === passId ? 'border-blue-500 bg-gray-800' : 'border-gray-700 bg-gray-900 hover:bg-gray-800'"
            :aria-current="p.id === passId ? 'true' : undefined"
            @click="select(p.id)"
          >
            <span class="block text-xs" :class="STATE_COLORS[p.state]">
              {{ p.state }}<span v-if="p.mode === 'test'" class="ml-1 rounded bg-yellow-900 px-1.5 text-yellow-300">test</span>
            </span>
            <span class="block text-xs text-gray-400">started {{ formatTime(p.started_at) }} by {{ p.started_by ?? '-' }}</span>
            <span class="block text-xs text-gray-500">
              {{ p.events }} event{{ p.events === 1 ? '' : 's' }}<template v-if="p.last_at"> · {{ formatTime(p.last_at) }}</template>
              · <span class="font-mono">{{ p.id }}</span>
            </span>
          </button>
          <p v-if="!c.passes.length" class="mt-1 text-xs text-gray-500">No pass yet: the first launch starts one.</p>
        </section>
      </details>
      <p v-if="!cycles.length && !loading" class="text-sm text-gray-500">No cycle yet.</p>
    </nav>

    <div class="min-w-0 space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <h1 class="text-2xl font-bold text-gray-100">{{ current ? `Journal · ${monthName(current.cycle)} · ${current.state}` : 'Cycle journal' }}</h1>
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <!-- A paused pass: resume it (the Dashboard continues it) or abandon it for good. The server has the last word. -->
          <template v-if="current?.state === 'paused'">
            <button
              class="rounded-md bg-blue-600 px-4 py-1.5 text-white hover:bg-blue-500 disabled:opacity-50"
              title="Continue this cycle on the Dashboard"
              @click="resume(current.id)"
            >
              Resume
            </button>
            <button class="rounded-md bg-gray-800 px-4 py-1.5 text-red-400 hover:bg-gray-700" @click="abandoning = true">Abandon</button>
          </template>
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
            :href="csvUrl(passId)"
            :class="{ 'pointer-events-none opacity-50': !passId }"
            download
          >
            Export CSV
          </a>
        </div>
      </div>

      <p class="text-xs text-gray-500">
        Every change of the pass (one run of the cycle), oldest first. Refused actions (409) are not events: see Tracking.
        Not seen: the <code>pridec</code> command line, build_analytics launched from DHIS2.
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
              <td colspan="6" class="px-4 py-6 text-center text-gray-500">No event for this pass.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Same detail as Tracking: the request, then the job logs. -->
      <RequestDialog
        :open="!!selected"
        :title="selected ? `${selected.event} · ${selected.item ?? selected.cycle}` : ''"
        :request="selected?.request"
        :job-id="selected?.job_id && JOB_EVENTS.has(selected.event) ? selected.job_id : null"
        @close="selected = null"
      />

      <ConfirmDialog :open="abandoning" title="Abandon this cycle?" confirm-label="Abandon" @confirm="confirmAbandon" @cancel="abandoning = false">
        The pass {{ current?.id }} of {{ current ? monthName(current.cycle) : '' }} stops for good: it cannot be resumed, and its
        open forecast run is abandoned. Its journal stays readable. The month can be run again in a new pass.
      </ConfirmDialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useJournal } from '@/composables/useJournal'
import type { JournalEvent, JournalPass, PassState } from '@/types/pipeline'
import RequestDialog from '@/views/TrackerView/components/RequestDialog.vue'
import ConfirmDialog from '@/views/Dashboard/components/ConfirmDialog.vue'

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
  paused: 'text-yellow-400',
  abandoned: 'text-red-400',
}
const STATE_COLORS: Record<PassState, string> = {
  active: 'text-blue-400',
  paused: 'text-yellow-300',
  complete: 'text-green-400',
  abandoned: 'text-red-400',
}

const route = useRoute()
const router = useRouter()
const { cycles, events, loading, error, load, loadCycles, csvUrl, resume, abandon } = useJournal()
const isAdmin = computed(() => useAuthStore().user?.is_admin === true)

// ?pass=<id> (the Dashboard link), else the newest pass of the target month once the list is loaded.
const query = route.query.pass
const passId = ref(typeof query === 'string' && /^[0-9a-f]{8}$/.test(query) ? query : '')
const step = ref('')
const selected = ref<JournalEvent | null>(null)
const abandoning = ref(false)

// Cycles come newest first: grouping keeps that order, years included.
const years = computed(() => {
  const groups = new Map<string, typeof cycles.value>()
  for (const c of cycles.value) groups.set(c.cycle.slice(0, 4), [...(groups.get(c.cycle.slice(0, 4)) ?? []), c])
  return [...groups]
})
const passes = computed<JournalPass[]>(() => cycles.value.flatMap(c => c.passes))
const current = computed(() => passes.value.find(p => p.id === passId.value))

const shown = computed(() => events.value.filter(e => !step.value || e.step === step.value))

const hasDetail = (e: JournalEvent) => e.request != null || (e.job_id != null && JOB_EVENTS.has(e.event))
const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
const formatDetail = (detail: Record<string, unknown>) =>
  Object.entries(detail).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`).join(' · ')

function select(id: string) {
  passId.value = id
  router.replace({ query: { ...route.query, pass: id } }) // shareable, kept on reload; Back leaves the page
  load(id)
}

async function refresh() {
  await loadCycles()
  passId.value ||= cycles.value.find(c => c.target)?.passes[0]?.id ?? passes.value[0]?.id ?? ''
  if (passId.value) await load(passId.value)
}

async function confirmAbandon() {
  abandoning.value = false
  if (current.value) await abandon(current.value.id)
}

onMounted(refresh)
</script>
