import { ref } from 'vue'
import { getFetchedImports } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { FetchedImport } from '@/types/pipeline'

/** The imports approval dialog of Data Import: the Pivot data elements fetched in this pass, read from etlhub. */
export function useFetchedImports() {
  const open = ref(false)
  const loading = ref(false)
  const error = ref('')
  const imports = ref<FetchedImport[] | null>(null)
  let request = 0 // drops the answer of a dialog closed meanwhile

  async function show(): Promise<void> {
    const id = ++request
    open.value = true
    loading.value = true
    error.value = ''
    imports.value = null
    try {
      const data = await getFetchedImports()
      if (id === request) imports.value = data
    } catch (err) {
      if (id === request) error.value = errorMessage(err, 'Could not read the fetched data')
    } finally {
      if (id === request) loading.value = false
    }
  }

  function close(): void {
    request++
    open.value = false
    loading.value = false
  }

  return { open, loading, error, imports, show, close }
}
