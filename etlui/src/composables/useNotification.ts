import { h, markRaw, reactive } from 'vue'
import toast from 'vue3-hot-toast'
import { trackingApi } from '@/services/api'
import JobToast from '@/components/JobToast.vue'

export const JOB_POLL_MS = 3000
export const JOB_END_MS = 5000

export interface JobEnd {
  success: boolean
  message: string
}

export interface JobStep {
  key: 'accepted' | 'running' | 'success' | 'error'
  at: string // local time the step was seen
  detail?: string
}

/** '42 s', '3 min 26 s', '1 h 05 min' */
export function formatElapsed(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s} s`
  if (s < 3600) return `${Math.floor(s / 60)} min ${s % 60} s`
  return `${Math.floor(s / 3600)} h ${String(Math.floor((s % 3600) / 60)).padStart(2, '0')} min`
}

const sleep = () => new Promise(resolve => setTimeout(resolve, JOB_POLL_MS))

// While the pointer is on the toasts, a toast whose time is up checks again this often.
export const LEAVE_MS = 1000

// vue3-hot-toast 0.0.5 does not pause on hover (its dismiss timers are never cleared): every toast is shown with an
// infinite duration and closed from here, never while the pointer is on the toasts (:hover reaches App.vue's layer).
function closeAfter(id: string, ms: number) {
  setTimeout(() => (document.querySelector('[data-toasts]:hover') ? closeAfter(id, LEAVE_MS) : toast.dismiss(id)), ms)
}

/**
 * One toast per job that keeps every step reached: accepted, running (with its elapsed time), then completed or failed.
 * It goes JOB_END_MS after the end, or once the pointer leaves it. Resolves with the end.
 */
async function followJob(label: string, jobId: string): Promise<JobEnd> {
  const started = Date.now()
  const view = reactive({ label, steps: [] as JobStep[] })
  const add = (key: JobStep['key'], detail?: string) => view.steps.push({ key, at: new Date().toLocaleTimeString(), detail })
  let workerMessage = '' // the running step's first message: the elapsed time follows it
  // The toast keeps this component: the steps update in place (markRaw: the toaster stores it in its own state).
  const content = markRaw({ render: () => h(JobToast, view) })

  add('accepted', `Queued for a worker · ${jobId}`)
  const id = toast.loading(content)
  for (;;) {
    let job: { status: string | null; message: string | null }
    try {
      job = (await trackingApi.getJobLogs(jobId)).data
    } catch (err) {
      // ponytail: retries a network error forever; give up after N tries if a dead etlhub must end the toast.
      if ((err as { response?: { status?: number } })?.response?.status !== 404) {
        await sleep()
        continue
      }
      job = { status: 'error', message: 'Job not found on the server' }
    }
    if (job.status === 'running') {
      const running = view.steps.find(s => s.key === 'running')
      if (!running) add('running', (workerMessage = job.message ?? 'Started by a worker'))
      else running.detail = `${workerMessage} · in progress for ${formatElapsed(Date.now() - started)}`
    }
    if (job.status === 'pending' || job.status === 'running') {
      await sleep()
      continue
    }
    // success, error, or null: the job record expired (24 h) before its end was seen
    const success = job.status === 'success'
    const message = job.message ?? job.status ?? 'Status unknown: the job record expired'
    add(success ? 'success' : 'error', `${message} · ${formatElapsed(Date.now() - started)}`)
    toast[success ? 'success' : 'error'](content, { id, duration: Number.POSITIVE_INFINITY })
    closeAfter(id, JOB_END_MS)
    return { success, message }
  }
}

export function useNotification() {
  const showNotification = (msg: string, type: 'success' | 'error') =>
    closeAfter(toast[type](msg, { duration: Number.POSITIVE_INFINITY }), 5000)
  return { showNotification, followJob }
}
