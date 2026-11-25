import { ref, watch, type Ref } from 'vue'
import { getJournal } from '@/services/pipeline'
import { errorMessage, type RequestLog } from '@/services/api'
import { coupleName, itemName } from '@/config/pipeline'
import type { Checkpoints, JournalEvent } from '@/types/pipeline'

export interface ActivityEntry {
  id: string
  action: string
  message: string
  time: string
  success: boolean
  jobId: string | null
  request: RequestLog | null // the tracked request, while etlhub keeps it
}

// The last requests of the pass shown in Recent Activity.
export const RECENT = 6
// Reads and mode switches are not the pass's work (as etlhub's pass counts): left out.
const LEFT_OUT = new Set(['availability_checked', 'availability_reused', 'mode_changed'])
const EVENT_TEXT: Record<string, string> = {
  succeeded: 'Completed', failed: 'Failed', launched: 'Launched (lock released since)', uploaded: 'File uploaded',
  removed: 'File removed', decided: 'Decided', skipped: 'Skipped', reset: 'Reset', run_opened: 'Run opened',
  run_closed: 'Run closed', run_abandoned: 'Run abandoned', pass_started: 'Pass started', paused: 'Paused',
  resumed: 'Resumed', abandoned: 'Pass abandoned', lock_released: 'Lock released', cycle_closed: 'Cycle closed'
}
const eventText = (event: string) => EVENT_TEXT[event] ?? event.replace(/_/g, ' ')
const COUPLE = /^(ADJ|COM|CSB)\/(Malaria|Diarrhea|Respinf):/

/** The journal's events (oldest first) as Recent Activity: the last RECENT requests, newest first, one line each. */
export function toActivity(events: JournalEvent[]): ActivityEntry[] {
  const seen = new Set<string>()
  const entries: ActivityEntry[] = []
  for (const e of [...events].reverse()) {
    if (!e.request_id || LEFT_OUT.has(e.event) || seen.has(e.request_id)) continue
    seen.add(e.request_id) // a request causing several events: its newest one
    const couple = e.item?.match(COUPLE)?.[0].slice(0, -1)
    entries.push({
      id: `${e.request_id}:${e.event}`,
      action: e.item ? itemName(e.item) : eventText(e.event),
      message: [eventText(e.event), couple && coupleName(couple), e.actor && `by ${e.actor}`].filter(Boolean).join(' · '),
      time: e.at.slice(0, 16).replace('T', ' '), // server local time, as the Journal shows it: never parsed
      success: e.event !== 'failed' && (e.request?.status_code ?? 200) < 400,
      jobId: e.job_id,
      request: e.request
    })
    if (entries.length === RECENT) break
  }
  return entries
}

/**
 * Recent Activity of the Forecast page: from etlhub's journal of the pass shown, so it survives a reload or a page
 * change. Read again at each new pipeline state (after every action, every 3 s while a job runs); last answer wins.
 */
export function usePassActivity(state: Ref<Checkpoints | null>) {
  const activity = ref<ActivityEntry[]>([])
  const error = ref('') // a failed read keeps the last list; the next state reads again
  let call = 0

  watch(state, async current => {
    const id = ++call
    const passId = current?.pass?.id
    if (!passId) {
      activity.value = []
      error.value = ''
      return
    }
    try {
      const events = await getJournal(passId)
      if (id !== call) return
      activity.value = toActivity(events)
      error.value = ''
    } catch (err) {
      if (id === call) error.value = errorMessage(err, 'Could not read the activity of this pass')
    }
  })

  return { activity, error }
}
