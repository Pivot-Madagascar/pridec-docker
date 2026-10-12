import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configService } from '@/services/config'
import { errorMessage } from '@/services/api'
import type { ConfigResponse, ConfigUpdate } from '@/types/config'

export const useConfigStore = defineStore('config', () => {
  const config = ref<ConfigResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function run(call: () => Promise<ConfigResponse>, fallback: string, rethrow = true) {
    loading.value = true
    error.value = null
    try {
      config.value = await call()
    } catch (e) {
      error.value = errorMessage(e, fallback)
      if (rethrow) throw e
    } finally {
      loading.value = false
    }
  }

  const fetchConfig = () => run(() => configService.get(), 'Failed to load config', false)
  const updateConfig = (payload: ConfigUpdate) => run(() => configService.update(payload), 'Failed to update config')
  const reloadConfig = () => run(() => configService.reload(), 'Failed to reload config')

  return { config, loading, error, fetchConfig, updateConfig, reloadConfig }
})
