import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFetchedImports } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { FetchedImport } from '@/types/pipeline'

/**
 * GET /pipeline/imports/fetched, kept across dialogs and pages: replaced only when the request is made again
 * (useFetchedImports: an import finished, another pass or mode, or Refresh). Never throws: a failure is in `error`.
 */
export const useFetchedImportsStore = defineStore('fetchedImports', () => {
  const imports = ref<FetchedImport[] | null>(null)
  const loading = ref(false)
  const error = ref('')
  const stamp = ref<string | null>(null) // what `imports` was read for (useFetchedImports' stamp)
  let request = 0 // only the latest answer is kept

  async function load(forStamp: string | null): Promise<void> {
    const id = ++request
    if (forStamp !== stamp.value) imports.value = null // another pass or mode: never show the previous one's data
    stamp.value = forStamp
    loading.value = true
    error.value = ''
    try {
      const data = await getFetchedImports()
      if (id === request) imports.value = data
    } catch (err) {
      if (id === request) error.value = errorMessage(err, 'Could not read the fetched data')
    } finally {
      if (id === request) loading.value = false
    }
  }

  return { imports, loading, error, stamp, load }
})
