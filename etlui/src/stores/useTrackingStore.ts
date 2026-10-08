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

  async function fetchRequests(limit = 50, endpoint?: string) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await trackingApi.listRequests(limit, endpoint)
      requests.value = data
    } catch (e: any) {
      error.value = e?.message || 'Failed to load tracking data'
    } finally {
      loading.value = false
    }
  }

  async function fetchRequest(requestId: string) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await trackingApi.getRequest(requestId)
      selected.value = data
    } catch (e: any) {
      error.value = e?.message || 'Failed to load request detail'
    } finally {
      loading.value = false
    }
  }

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
