import { describe, it, expect, vi, beforeEach } from 'vitest'

const post = vi.fn()
const get = vi.fn()
const del = vi.fn()
vi.mock('@/services/api', () => ({
  default: {
    post: (...args: unknown[]) => post(...args),
    get: (...args: unknown[]) => get(...args),
    delete: (...args: unknown[]) => del(...args)
  }
}))

import { uploadInputFile, getInputFiles, deleteInputFile, getConfigPreview, getExternalDataPreview } from '@/services/inputs'

describe('uploadInputFile', () => {
  beforeEach(() => vi.clearAllMocks())

  it('posts one file as multipart to /input/files/{name}', async () => {
    post.mockResolvedValue({ data: { saved: 'input/external_data.csv' } })
    const file = new File(['orgUnit,period'], 'data.csv')

    const saved = await uploadInputFile('external_data', file)

    expect(saved).toBe('input/external_data.csv')
    const [url, body, options] = post.mock.calls[0]
    expect(url).toBe('/input/files/external_data')
    expect(body).toBeInstanceOf(FormData)
    expect((body as FormData).get('file')).toBe(file)
    expect(options.headers['Content-Type']).toBe('multipart/form-data')
  })
})

describe('getInputFiles', () => {
  it('reads the server state from /input/files', async () => {
    const state = { config: { exists: true, size: 12, modified: '2026-10-05T13:50:00' }, external_data: { exists: false } }
    get.mockResolvedValue({ data: state })

    expect(await getInputFiles()).toEqual(state)
    expect(get).toHaveBeenCalledWith('/input/files')
  })
})

describe('deleteInputFile', () => {
  it('sends DELETE /input/files/{name}', async () => {
    del.mockResolvedValue({ data: { deleted: 'input/external_data.csv' } })

    expect(await deleteInputFile('external_data')).toBe('input/external_data.csv')
    expect(del).toHaveBeenCalledWith('/input/files/external_data')
  })
})

describe('preview endpoints', () => {
  it('getConfigPreview reads /input/files/config/preview', async () => {
    get.mockResolvedValue({ data: { a: 1 } })

    expect(await getConfigPreview()).toEqual({ a: 1 })
    expect(get).toHaveBeenCalledWith('/input/files/config/preview')
  })

  it('getExternalDataPreview sends the row limit as a query param', async () => {
    const data = { columns: ['a'], rows: [], total_rows: 0, period_range: null, org_units: 0 }
    get.mockResolvedValue({ data })

    expect(await getExternalDataPreview(100)).toEqual(data)
    expect(get).toHaveBeenCalledWith('/input/files/external_data/preview', { params: { limit: 100 } })
  })
})
