import { ref } from 'vue'
import type { LaunchedJob } from '@/services/pipeline'

export interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
  jobId?: string | null
  // The tracked request that started the job (X-Request-ID sent by launchJob)
  requestId?: string
}

export function useActivityLog() {
  const activityLog = ref<ActivityEntry[]>([])

  const addActivity = (action: string, message: string, success: boolean, job?: LaunchedJob) => {
    activityLog.value.unshift({
      id: Date.now() + Math.random(),
      action,
      message,
      time: new Date().toLocaleTimeString(),
      success,
      ...job
    })
    if (activityLog.value.length > 20) {
      activityLog.value = activityLog.value.slice(0, 20)
    }
  }

  return {
    activityLog,
    addActivity,
  }
}