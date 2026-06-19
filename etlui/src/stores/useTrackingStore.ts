import { defineStore } from 'pinia'
import { ref } from 'vue'
import { trackingApi } from '@/services/api'
import type { RequestLog } from '@/services/api'

export const useTrackingStore = defineStore('tracking', () => {
  const requests = ref<RequestLog[]>([])
  const selected = ref<RequestLog | null>(null)
  const loading = ref(false)
  const error = ref('')

  let timer: number | null = null

  async function fetchRequests(limit = 50) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await trackingApi.listRequests(limit)
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

  function startPolling(limit = 50) {
    stopPolling()
    fetchRequests(limit)
    timer = window.setInterval(() => fetchRequests(limit), 2000)
  }

  function stopPolling() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  return {
    requests,
    selected,
    loading,
    error,
    fetchRequests,
    fetchRequest,
    startPolling,
    stopPolling,
  }
})
