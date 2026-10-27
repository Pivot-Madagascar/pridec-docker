import { ref, getCurrentScope, onScopeDispose } from 'vue'
import * as pipeline from '@/services/pipeline'
import { applyDefaultFile, deleteInputFile, getDefaultFiles, getInputFiles, uploadInputFile } from '@/services/inputs'
import { useNotification } from '@/composables/useNotification'
import { errorMessage } from '@/services/api'
import { plainError } from '@/config/pipeline'
import type { Checkpoints, ConfirmationRequired, Disease, Source } from '@/types/pipeline'
import type { DefaultFile, InputName, ServerFile } from '@/types/inputs'

// While a job holds the lock, the state is read again at this pace until the lock is free.
export const POLL_MS = 3000

type AddActivity = (action: string, message: string, success: boolean, job?: pipeline.LaunchedJob) => void
type Call = (confirm: boolean) => Promise<unknown>

export interface PendingConfirmation {
  label: string
  message: string
  impact: Record<string, unknown>
  retry: () => Promise<boolean>
}

interface HttpError {
  response?: { status?: number; data?: { code?: unknown } }
}

function confirmationRequired(err: unknown): ConfirmationRequired | null {
  const response = (err as HttpError)?.response
  return response?.status === 409 && response.data?.code === 'confirmation_required'
    ? (response.data as ConfirmationRequired)
    : null
}

const isLaunchedJob = (r: unknown): r is pipeline.LaunchedJob => typeof r === 'object' && r !== null && 'requestId' in r

/** The pipeline state from etlhub, and every action on it. The server decides: nothing is computed here. */
export function usePipeline(addActivity: AddActivity) {
  const { showNotification, followJob } = useNotification()
  const state = ref<Checkpoints | null>(null)
  const serverFiles = ref<Partial<Record<InputName, ServerFile>>>({})
  const defaults = ref<Record<string, DefaultFile>>({})
  const busy = ref(false)
  const pending = ref<PendingConfirmation | null>(null)
  let timer: ReturnType<typeof setTimeout> | null = null

  const stop = () => {
    if (timer !== null) clearTimeout(timer)
    timer = null
  }

  const refresh = async (): Promise<void> => {
    stop()
    try {
      const [checkpoints, files, defaultFiles] = await Promise.all([pipeline.getCheckpoints(), getInputFiles(), getDefaultFiles()])
      state.value = checkpoints
      serverFiles.value = files
      defaults.value = defaultFiles
    } catch {
      showNotification('Could not read the pipeline state', 'error')
    }
    if (state.value?.lock) timer = setTimeout(refresh, POLL_MS) // follow the running job until it ends
  }

  // Runs one action. A 409 confirmation_required keeps it in `pending` until the user confirms or cancels.
  const act = async (label: string, call: Call, confirm = false): Promise<boolean> => {
    busy.value = true
    try {
      const result = await call(confirm)
      if (isLaunchedJob(result) && result.jobId) {
        // The toast follows the job; the activity is its end, not the 202 (RecentActivity's Detail opens the request and logs)
        void followJob(label, result.jobId).then(end => addActivity(label, end.message, end.success, result))
      } else {
        showNotification(`${label}: success`, 'success')
        addActivity(label, 'Success', true)
      }
      return true
    } catch (err) {
      const confirmation = confirmationRequired(err)
      if (confirmation) {
        pending.value = { label, message: confirmation.message, impact: confirmation.impact, retry: () => act(label, call, true) }
        return false
      }
      const message = plainError(errorMessage(err, `${label} failed`))
      showNotification(message, 'error')
      addActivity(label, message, false)
      return false
    } finally {
      busy.value = false
      await refresh()
    }
  }

  const confirm = async (): Promise<boolean> => {
    const current = pending.value
    pending.value = null
    return current ? current.retry() : false
  }

  if (getCurrentScope()) onScopeDispose(stop)

  return {
    state, serverFiles, defaults, busy, pending, refresh, stop, confirm,
    cancel: () => { pending.value = null },
    launch: (task: string, label: string) => act(label, c => pipeline.launchJob(task, c)),
    openRun: (source: Source, disease: Disease) => act(`Open run ${source}/${disease}`, c => pipeline.openRun(source, disease, c)),
    abandonRun: () => act('Abandon run', () => pipeline.abandonRun()),
    decide: (decision: 'approve' | 'reject') => act(decision === 'approve' ? 'Approve forecast' : 'Reject forecast', () => pipeline.decideRun(decision)),
    skipAlerts: () => act('Skip alert thresholds', () => pipeline.skipAlerts()),
    decideImports: (decision: 'approve' | 'reject') => act(decision === 'approve' ? 'Approve imports' : 'Reject imports', () => pipeline.decideImports(decision)),
    setMode: (testMode: boolean) => act(testMode ? 'Switch to test mode' : 'Switch to production', () => pipeline.setMode(testMode)),
    setCycle: (cycle: string | null) => act(`Cycle ${cycle ?? 'of the current month'}`, () => pipeline.setCycle(cycle)),
    pause: () => act('Pause the cycle', () => pipeline.pausePass()),
    resume: (passId: string) => act('Resume the cycle', () => pipeline.resumePass(passId)),
    abandonPass: (passId: string) => act('Abandon the cycle', () => pipeline.abandonPass(passId)),
    releaseLock: () => act('Release lock', () => pipeline.releaseLock()),
    upload: (name: InputName, file: File) => act(`Upload ${name}`, c => uploadInputFile(name, file, c)),
    remove: (name: InputName) => act(`Delete ${name}`, c => deleteInputFile(name, c)),
    useDefault: (name: InputName) => act(`Use the default ${name}`, c => applyDefaultFile(name, c))
  }
}
