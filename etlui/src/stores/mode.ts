import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCheckpoints } from '@/services/pipeline'
import type { Checkpoints } from '@/types/pipeline'

/**
 * The user's mode for the header (ModeBadge): etlhub's `test_mode` and `dry_run` (DRYRUN = TEST MODE), never computed
 * here. Read at login (`load`), then kept up to date by every state usePipeline reads (`set`), so right after a change.
 * null: unknown (logged out, or etlhub could not answer); the header then shows nothing.
 */
export const useModeStore = defineStore('mode', () => {
  const testMode = ref<boolean | null>(null)
  const dryRun = ref<boolean | null>(null)

  function set(state: Pick<Checkpoints, 'test_mode' | 'dry_run'> | null): void {
    testMode.value = state?.test_mode ?? null
    dryRun.value = state?.dry_run ?? null
  }

  async function load(): Promise<void> {
    try {
      set(await getCheckpoints())
    } catch {
      set(null) // the pages report etlhub's errors; the header only stops showing a mode it no longer knows
    }
  }

  return { testMode, dryRun, set, load }
})
