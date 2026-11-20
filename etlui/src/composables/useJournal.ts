import { ref } from 'vue'
import { abandonPass, getCheckpoints, getCycles, getJournal, journalCsvUrl, releaseLock, resumePass } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import { confirmationRequired } from '@/composables/usePipeline'
import type { ConfirmationRequired, JournalCycle, JournalEvent, PipelineLock } from '@/types/pipeline'

/** The months and their passes, the journal of one pass, resuming or abandoning a paused pass, and the job lock, as etlhub answers. */
export function useJournal() {
  const cycles = ref<JournalCycle[]>([])
  const events = ref<JournalEvent[]>([])
  const lock = ref<PipelineLock | null>(null)
  // The 409 etlhub sent while the job holding the lock may still run: the user confirms it, or cancels.
  const pendingRelease = ref<ConfirmationRequired | null>(null)
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

  async function loadLock(): Promise<void> {
    try {
      lock.value = (await getCheckpoints()).lock
    } catch (err) {
      error.value = errorMessage(err, 'Could not read the job lock')
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
    cycles, events, lock, pendingRelease, loading, error, load, loadCycles, loadLock, csvUrl: journalCsvUrl,
    resume: (passId: string) => act(() => resumePass(passId), passId),
    abandon: (passId: string) => act(() => abandonPass(passId), passId),
    // A lock left by a dead worker (it never expires): its job becomes error, lock_released goes to the job's pass.
    // etlhub frees it at once when no worker runs the job; otherwise its 409 waits in pendingRelease (confirm = true).
    releaseLock: async (passId: string, confirm = false) => {
      pendingRelease.value = null
      await act(async () => {
        try {
          await releaseLock(confirm)
        } catch (err) {
          pendingRelease.value = confirmationRequired(err)
          if (!pendingRelease.value) throw err
        }
      }, passId)
      await loadLock()
    }
  }
}
