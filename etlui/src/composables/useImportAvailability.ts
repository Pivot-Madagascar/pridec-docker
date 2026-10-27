import { ref } from 'vue'
import { getImportAvailability } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { ImportAvailabilityReport } from '@/types/pipeline'

/** The "Details" dialog of Data Import: etlhub's report on the imported data, shared in the cycle (etlhub decides
 * which sections it reuses); `load(true)` (Refresh) makes it ask DHIS2 again for every section. */
export function useImportAvailability() {
  const open = ref(false)
  const loading = ref(false)
  const error = ref('')
  const report = ref<ImportAvailabilityReport | null>(null)
  let request = 0 // drops the answer of a check that was closed or replaced meanwhile

  async function load(refresh = false): Promise<void> {
    const id = ++request
    loading.value = true
    error.value = ''
    report.value = null
    try {
      const data = await getImportAvailability(refresh)
      if (id === request) report.value = data
    } catch (err) {
      if (id === request) error.value = errorMessage(err, 'Could not check the imported data')
    } finally {
      if (id === request) loading.value = false
    }
  }

  // The dialog opens at once, with the loader, while etlhub asks DHIS2.
  function show(): Promise<void> {
    open.value = true
    return load()
  }

  function close(): void {
    request++
    open.value = false
    loading.value = false
  }

  return { open, loading, error, report, show, load, close }
}
