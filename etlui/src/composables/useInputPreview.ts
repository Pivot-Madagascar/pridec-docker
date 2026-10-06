import { ref } from 'vue'
import { getConfigPreview, getExternalDataPreview } from '@/services/inputs'
import { previewCsvStream } from '@/utils/preview'
import type { ConfigData, CsvPreviewData, InputName } from '@/types/inputs'

export const PREVIEW_ROWS = 100

type Source = 'server' | 'local'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return err instanceof Error ? err.message : 'Preview failed'
}

async function readLocalConfig(file: File): Promise<ConfigData> {
  const data: unknown = JSON.parse(await file.text())
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    throw new Error('config.json must be a JSON object')
  }
  return data as ConfigData
}

/** Preview of input/config.json or input/external_data.csv, from the server or from a selected File. */
export function useInputPreview() {
  const current = ref<{ name: InputName; source: Source } | null>(null)
  const loading = ref(false)
  const error = ref('')
  const config = ref<ConfigData | null>(null)
  const csv = ref<CsvPreviewData | null>(null)
  let request = 0 // drops answers of a preview that was replaced or closed

  const reset = () => {
    request++
    loading.value = false
    error.value = ''
    config.value = null
    csv.value = null
  }

  const open = async (name: InputName, from: File | 'server'): Promise<void> => {
    reset()
    const id = request
    current.value = { name, source: from === 'server' ? 'server' : 'local' }
    loading.value = true
    try {
      if (name === 'config') {
        const data = from === 'server' ? await getConfigPreview() : await readLocalConfig(from)
        if (id === request) config.value = data
      } else {
        const data =
          from === 'server' ? await getExternalDataPreview(PREVIEW_ROWS) : await previewCsvStream(from.stream(), PREVIEW_ROWS)
        if (id === request) csv.value = data
      }
    } catch (err) {
      if (id === request) error.value = errorMessage(err)
    } finally {
      if (id === request) loading.value = false
    }
  }

  const close = () => {
    reset()
    current.value = null
  }

  return { current, loading, error, config, csv, open, close }
}
