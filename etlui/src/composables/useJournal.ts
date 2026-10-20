import { ref } from 'vue'
import { getCycles, getJournal, journalCsvUrl } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { JournalCycle, JournalEvent } from '@/types/pipeline'

/** The cycles that have a history, and the journal of one of them, as etlhub returns them. */
export function useJournal() {
  const cycles = ref<JournalCycle[]>([])
  const events = ref<JournalEvent[]>([])
  const loading = ref(false)
  const error = ref('')
  let request = 0 // drops the answer of a cycle that was replaced meanwhile

  async function load(cycle: string): Promise<void> {
    const id = ++request
    loading.value = true
    error.value = ''
    try {
      const data = await getJournal(cycle)
      if (id === request) events.value = data
    } catch (err) {
      if (id !== request) return
      events.value = []
      error.value = errorMessage(err, 'Could not load the journal')
    } finally {
      if (id === request) loading.value = false
    }
  }

  async function loadCycles(): Promise<void> {
    try {
      cycles.value = await getCycles()
    } catch (err) {
      error.value = errorMessage(err, 'Could not load the cycles')
    }
  }

  return { cycles, events, loading, error, load, loadCycles, csvUrl: journalCsvUrl }
}
