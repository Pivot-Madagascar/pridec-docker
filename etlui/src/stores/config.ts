import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configService } from '@/services/config'
import type { ConfigResponse } from '@/types/config'

export const useConfigStore = defineStore('config', () => {
  const config = ref<ConfigResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchConfig() {
    loading.value = true
    error.value = null
    try {
      config.value = await configService.get()
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Failed to load config'
    } finally {
      loading.value = false
    }
  }

  async function updateConfig(payload: Partial<ConfigResponse>) {
    loading.value = true
    error.value = null
    try {
      config.value = await configService.update(payload)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Failed to update config'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function reloadConfig() {
    loading.value = true
    error.value = null
    try {
      config.value = await configService.reload()
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Failed to reload config'
      throw e
    } finally {
      loading.value = false
    }
  }

  return { config, loading, error, fetchConfig, updateConfig, reloadConfig }
})