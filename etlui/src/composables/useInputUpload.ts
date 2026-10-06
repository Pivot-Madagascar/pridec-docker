import { ref } from 'vue'
import { uploadInputFile, getInputFiles, deleteInputFile } from '@/services/inputs'
import type { InputName, ServerFile } from '@/types/inputs'
import { useNotification } from '@/composables/useNotification'

const UPLOAD_ACTIVITY = 'Upload Input File'
const DELETE_ACTIVITY = 'Delete Input File'

function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  // FastAPI sends a string for our 404/413/422, a list for missing fields.
  return typeof detail === 'string' ? detail : fallback
}

type AddActivity = (action: string, message: string, success: boolean) => void

// addActivity comes from the caller: useActivityLog() state is per call, not shared.
export function useInputUpload(addActivity: AddActivity) {
  const { showNotification } = useNotification()
  const uploading = ref<InputName | null>(null)
  const deleting = ref<InputName | null>(null)
  const serverFiles = ref<Partial<Record<InputName, ServerFile>>>({})

  const refresh = async (): Promise<void> => {
    try {
      serverFiles.value = await getInputFiles()
    } catch {
      serverFiles.value = {}
      showNotification('Could not read the files in input/', 'error')
    }
  }

  const upload = async (name: InputName, file: File): Promise<boolean> => {
    uploading.value = name
    try {
      const saved = await uploadInputFile(name, file)
      showNotification(`Uploaded ${saved}. Run "Validate inputs" again before the forecast.`, 'success')
      addActivity(UPLOAD_ACTIVITY, `Saved ${saved}`, true)
      await refresh()
      return true
    } catch (err) {
      const message = errorMessage(err, 'Upload failed')
      showNotification(message, 'error')
      addActivity(UPLOAD_ACTIVITY, message, false)
      return false
    } finally {
      uploading.value = null
    }
  }

  const remove = async (name: InputName): Promise<boolean> => {
    deleting.value = name
    try {
      const deleted = await deleteInputFile(name)
      showNotification(`Deleted ${deleted}. Run "Validate inputs" again before the forecast.`, 'success')
      addActivity(DELETE_ACTIVITY, `Deleted ${deleted}`, true)
      return true
    } catch (err) {
      const message = errorMessage(err, 'Delete failed')
      showNotification(message, 'error')
      addActivity(DELETE_ACTIVITY, message, false)
      return false
    } finally {
      await refresh()
      deleting.value = null
    }
  }

  return { uploading, deleting, serverFiles, refresh, upload, remove }
}
