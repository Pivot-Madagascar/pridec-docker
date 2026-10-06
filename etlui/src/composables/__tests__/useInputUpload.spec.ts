import { describe, it, expect, vi, beforeEach } from 'vitest'

const uploadInputFile = vi.fn()
const getInputFiles = vi.fn()
const deleteInputFile = vi.fn()
const showNotification = vi.fn()
const addActivity = vi.fn()
vi.mock('@/services/inputs', () => ({
  uploadInputFile: (...args: unknown[]) => uploadInputFile(...args),
  getInputFiles: (...args: unknown[]) => getInputFiles(...args),
  deleteInputFile: (...args: unknown[]) => deleteInputFile(...args)
}))
vi.mock('@/composables/useNotification', () => ({ useNotification: () => ({ showNotification }) }))

import { useInputUpload } from '@/composables/useInputUpload'

const config = new File(['{}'], 'config.json')
const externalData = new File(['orgUnit,period'], 'external_data.csv')
const SERVER_STATE = { config: { exists: true, size: 2, modified: '2026-10-05T13:50:00' }, external_data: { exists: false } }

describe('useInputUpload', () => {
  beforeEach(() => vi.clearAllMocks())

  it('notifies success, asks to re-run validation and refreshes the server state', async () => {
    getInputFiles.mockResolvedValue(SERVER_STATE)
    uploadInputFile.mockResolvedValue('input/config.json')
    const { upload, uploading } = useInputUpload(addActivity)

    const pending = upload('config', config)
    expect(uploading.value).toBe('config')
    const ok = await pending

    expect(ok).toBe(true)
    expect(uploading.value).toBeNull()
    expect(uploadInputFile).toHaveBeenCalledWith('config', config)
    expect(showNotification).toHaveBeenCalledWith(expect.stringContaining('Validate inputs'), 'success')
    expect(addActivity).toHaveBeenCalledWith('Upload Input File', 'Saved input/config.json', true)
    expect(getInputFiles).toHaveBeenCalled()
  })

  it('shows the backend detail on a 422', async () => {
    uploadInputFile.mockRejectedValue({ response: { status: 422, data: { detail: 'external_data.csv is missing columns: period' } } })
    const { upload, uploading } = useInputUpload(addActivity)

    const ok = await upload('external_data', externalData)

    expect(ok).toBe(false)
    expect(uploading.value).toBeNull()
    expect(showNotification).toHaveBeenCalledWith('external_data.csv is missing columns: period', 'error')
    expect(addActivity).toHaveBeenCalledWith('Upload Input File', 'external_data.csv is missing columns: period', false)
  })

  it('falls back to a generic message when there is no string detail', async () => {
    uploadInputFile.mockRejectedValue(new Error('Network Error'))
    const { upload } = useInputUpload(addActivity)

    expect(await upload('config', config)).toBe(false)
    expect(showNotification).toHaveBeenCalledWith('Upload failed', 'error')
  })
})

describe('useInputUpload server files', () => {
  beforeEach(() => vi.clearAllMocks())

  it('refresh() loads the server state', async () => {
    getInputFiles.mockResolvedValue(SERVER_STATE)
    const { refresh, serverFiles } = useInputUpload(addActivity)

    await refresh()

    expect(serverFiles.value).toEqual(SERVER_STATE)
  })

  it('refresh() notifies when the server cannot be read', async () => {
    getInputFiles.mockRejectedValue(new Error('Network Error'))
    const { refresh, serverFiles } = useInputUpload(addActivity)

    await refresh()

    expect(serverFiles.value).toEqual({})
    expect(showNotification).toHaveBeenCalledWith('Could not read the files in input/', 'error')
  })

  it('remove() deletes the file, notifies and refreshes', async () => {
    deleteInputFile.mockResolvedValue('input/config.json')
    getInputFiles.mockResolvedValue({ config: { exists: false }, external_data: { exists: false } })
    const { remove, deleting, serverFiles } = useInputUpload(addActivity)

    const ok = await remove('config')

    expect(ok).toBe(true)
    expect(deleting.value).toBeNull()
    expect(deleteInputFile).toHaveBeenCalledWith('config')
    expect(showNotification).toHaveBeenCalledWith(expect.stringContaining('input/config.json'), 'success')
    expect(addActivity).toHaveBeenCalledWith('Delete Input File', 'Deleted input/config.json', true)
    expect(serverFiles.value.config).toEqual({ exists: false })
  })

  it('remove() shows the backend detail on failure and still refreshes', async () => {
    deleteInputFile.mockRejectedValue({ response: { status: 404, data: { detail: 'config is not in input/' } } })
    getInputFiles.mockResolvedValue(SERVER_STATE)
    const { remove, deleting } = useInputUpload(addActivity)

    expect(await remove('config')).toBe(false)
    expect(deleting.value).toBeNull()
    expect(showNotification).toHaveBeenCalledWith('config is not in input/', 'error')
    expect(getInputFiles).toHaveBeenCalled()
  })
})
