import { ref } from 'vue'
import { abandonPass, getCycles, getJournal, journalCsvUrl, resumePass } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { JournalCycle, JournalEvent } from '@/types/pipeline'

/** The months and their passes, the journal of one pass, and resuming or abandoning a paused pass, as etlhub answers. */
export function useJournal() {
  const cycles = ref<JournalCycle[]>([])
  const events = ref<JournalEvent[]>([])
  const loading = ref(false)
  const error = ref('')
  let request = 0 // drops the answer of a pass that was replaced meanwhile

  async function load(passId: string): Promise<void> {
    const id = ++request
    loading.value = true
    error.value = ''
    try {
      const data = await getJournal(passId)
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

  // The server refuses (409) a pass of the other mode or while another one is active: its message is shown.
  async function act(call: () => Promise<unknown>, passId: string): Promise<void> {
    let refused = ''
    try {
      await call()
    } catch (err) {
      refused = errorMessage(err, 'The server refused the action')
    }
    await Promise.all([loadCycles(), load(passId)]) // load clears the error: the refusal is set after it
    if (refused) error.value = refused
  }

  return {
    cycles, events, loading, error, load, loadCycles, csvUrl: journalCsvUrl,
    resume: (passId: string) => act(() => resumePass(passId), passId),
    abandon: (passId: string) => act(() => abandonPass(passId), passId)
  }
}
