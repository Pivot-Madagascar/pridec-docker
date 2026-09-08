import { ref } from 'vue'
import type { ActivityEntry } from '@/types/etl'

export function useActivityLog() {
  const activityLog = ref<ActivityEntry[]>([])

  const addActivity = (action: string, message: string, success: boolean, jobId?: string) => {
    activityLog.value.unshift({
      id: Date.now() + Math.random(),
      action,
      message,
      time: new Date().toLocaleTimeString(),
      success,
      jobId
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