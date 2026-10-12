import { defineStore } from 'pinia'
import { ref } from 'vue'
import { trackingApi } from '@/services/api'
import type { JobLogs, RequestLog } from '@/services/api'

export const useTrackingStore = defineStore('tracking', () => {
  const requests = ref<RequestLog[]>([])
  const selected = ref<RequestLog | null>(null)
  const loading = ref(false)
  const error = ref('')
  const jobLogs = ref<JobLogs | null>(null)
  const jobLogsLoading = ref(false)
  const jobLogsError = ref('')

  async function load(work: () => Promise<void>, fallback: string) {
    loading.value = true
    error.value = ''
    try {
      await work()
    } catch (e: any) {
      error.value = e?.message || fallback
    } finally {
      loading.value = false
    }
  }

  const fetchRequests = (limit = 50, endpoint?: string) =>
    load(async () => { requests.value = (await trackingApi.listRequests(limit, endpoint)).data }, 'Failed to load tracking data')

  const fetchRequest = (requestId: string) =>
    load(async () => { selected.value = (await trackingApi.getRequest(requestId)).data }, 'Failed to load request detail')

  async function fetchJobLogs(jobId: string) {
    jobLogsLoading.value = true
    jobLogsError.value = ''
    try {
      const { data } = await trackingApi.getJobLogs(jobId)
      jobLogs.value = data
    } catch (e: any) {
      jobLogs.value = null
      jobLogsError.value = e?.response?.status === 404
        ? 'No logs found for this job (job records are kept 24 h).'
        : e?.message || 'Failed to load job logs'
    } finally {
      jobLogsLoading.value = false
    }
  }

  return {
    requests,
    selected,
    loading,
    error,
    fetchRequests,
    fetchRequest,
    jobLogs,
    jobLogsLoading,
    jobLogsError,
    fetchJobLogs,
  }
})
